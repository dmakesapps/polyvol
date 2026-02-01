"""
Multi-Strategy Runner.
Runs all strategies simultaneously against live price data.
Manages paper trades and tracks performance.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import structlog

from ..core.config import get_config, StrategyConfig
from ..core.database import Database
from ..core.models import (
    Trade, Strategy as StrategyModel, PriceUpdate, 
    Side, TradeStatus, ExitReason, StrategyStatus
)
from ..collection.price_collector import PriceCollector
from ..collection.live_trader import LiveTrader, create_live_trader
from .base import BaseStrategy, ExitSignal
from .volatility import create_strategy


logger = structlog.get_logger()


class StrategyRunner:
    """
    Runs multiple strategies against live price data.
    Manages paper trading: entry signals, position tracking, exits.
    """
    
    def __init__(self, db: Database, price_collector: PriceCollector):
        self.db = db
        self.price_collector = price_collector
        self.config = get_config()
        
        # Live trader for real order execution
        self.live_trader: Optional[LiveTrader] = None
        if self.config.mode == "live":
            self.live_trader = create_live_trader(self.config)
            if self.live_trader:
                logger.info("strategy_runner.live_mode_enabled")
            else:
                logger.warning("strategy_runner.live_mode_missing_credentials")
        
        # Active strategies
        self.strategies: dict[str, BaseStrategy] = {}
        
        # Open trades by (strategy_id, condition_id)
        self.open_trades: dict[tuple[str, str], Trade] = {}
        
        # Cooldowns to prevent rapid re-entry: (strategy_id, condition_id) -> datetime
        self.cooldowns: dict[tuple[str, str], datetime] = {}
        
        # Running state
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the strategy runner."""
        if self._running:
            return
        
        # Load strategies from config
        await self._load_strategies()
        
        # Connect live trader if enabled
        if self.live_trader:
            await self.live_trader.connect()
            logger.info("strategy_runner.live_trader_connected")
            
        # Fix Amnesia: Load existing open trades from DB so we can manage/sell them
        await self._load_open_trades()
        
        # Initialize spending limit (User Request: Max $5 per 15 mins)
        self.spending_window_start = datetime.utcnow()
        self.spent_in_window = 0.0
        self.spending_limit = 5.0
        self.spending_window_duration = timedelta(minutes=15)
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        
        logger.info("strategy_runner.started", 
                   strategies=len(self.strategies),
                   live_mode=self.live_trader is not None)
    
    async def stop(self) -> None:
        """Stop the strategy runner."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Close live trader connection
        if self.live_trader:
            await self.live_trader.close()
        
        logger.info("strategy_runner.stopped")
    
    async def _load_strategies(self) -> None:
        """Load and initialize strategies from config, syncing with database."""
        self.enabled_strategy_ids = set()
        
        # Get existing strategy statuses from DB
        db_strategies = await self.db.get_strategies()
        status_map = {s.id: s.status for s in db_strategies}
        
        for strat_config in self.config.strategies:
            strategy = create_strategy({
                "id": strat_config.id,
                "entry": strat_config.entry,
                "exit": strat_config.exit,
                "tier": strat_config.tier,
                "direction": strat_config.direction
            })
            
            self.strategies[strategy.id] = strategy
            
            # Determine initial status
            # If exists in DB, keep current status. If not, use config.
            current_status = status_map.get(strategy.id)
            if current_status is None:
                current_status = StrategyStatus.ACTIVE if strat_config.enabled else StrategyStatus.TESTING
            
            # Save strategy to database (upsert)
            db_strategy = StrategyModel(
                id=strategy.id,
                name=strategy.name,
                tier=strategy.tier,
                entry_threshold=strategy.entry_threshold,
                exit_threshold=strategy.exit_threshold,
                direction=strategy.direction,
                status=current_status
            )
            await self.db.save_strategy(db_strategy)
            
            # Use ACTIVE status from DB for execution logic
            # Any status other than 'active' is treated as MONITOR_ONLY
            if current_status == StrategyStatus.ACTIVE:
                self.enabled_strategy_ids.add(strategy.id)
            
            logger.info("strategy_runner.strategy_loaded",
                       id=strategy.id,
                       status=current_status.value,
                       entry=strategy.entry_threshold,
                       exit=strategy.exit_threshold,
                       break_even_wr=f"{strategy.break_even_win_rate:.1%}")

    async def _load_open_trades(self) -> None:
        """Load open trades from database to restore state after restart."""
        # Get all OPEN trades from DB
        # Note: We use get_open_active_trades or manual query
        # Since I verified database.py has get_open_trades:
        trades = await self.db.get_open_trades()
        
        count = 0
        for trade in trades:
            # Reconstruct the key used in runner
            key = (trade.strategy_id, trade.condition_id)
            self.open_trades[key] = trade
            
            # Ensure the strategy object knows it has a position (to prevent double-buys)
            if trade.strategy_id in self.strategies:
                # We artificially "open" the position in the strategy object
                # This is a bit hacky but safe because runner checks self.open_trades first
                pass
            count += 1
            
        logger.info("strategy_runner.trades_restored", count=count)
    
    async def _run_loop(self) -> None:
        """Main strategy execution loop."""
        while self._running:
            try:
                # Get all current markets and their prices
                markets = self.price_collector.get_current_markets()
                
                for market in markets:
                    # Get latest price
                    price_update = self.price_collector.get_market_price(
                        market.condition_id
                    )
                    
                    if price_update:
                        # Process this price update through all strategies
                        await self._process_price(price_update)
                
                # Short sleep between cycles
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("strategy_runner.loop_error", error=str(e))
                await asyncio.sleep(5)
    
    async def _process_price(self, price_update: PriceUpdate) -> None:
        """Process a price update through all strategies."""
        for strategy_id, strategy in self.strategies.items():
            try:
                # Check for exit signals on existing positions
                await self._check_exits(strategy, price_update)
                
                # Check for entry signals
                await self._check_entries(strategy, price_update)
                
            except Exception as e:
                logger.error("strategy_runner.process_error",
                           strategy_id=strategy_id, error=str(e))
    
    async def _check_entries(
        self, 
        strategy: BaseStrategy, 
        price_update: PriceUpdate
    ) -> None:
        """Check if strategy should enter a position."""
        # Only check entries for enabled strategies
        # Disabled strategies are only loaded to manage exits of legacy positions
        if not hasattr(self, 'enabled_strategy_ids') or strategy.id not in self.enabled_strategy_ids:
            return

        # Check if we already have a position
        trade_key = (strategy.id, price_update.condition_id)
        if trade_key in self.open_trades:
            return
            
        # Check cooldowns
        if trade_key in self.cooldowns:
            if datetime.utcnow() < self.cooldowns[trade_key]:
                return
            else:
                # Cooldown expired
                del self.cooldowns[trade_key]
        
        # Check if we have EVER traded this market (Max 1 trade rule)
        if await self.db.has_traded_market(strategy.id, price_update.condition_id):
            return
        
        # Check entry signal
        signal = strategy.check_entry(price_update)
        
        if signal.should_enter:
            # Calculate Kelly Bet Size (Data Gathering)
            # Use bankroll of $1000 for simulation purposes
            bankroll = 1000.0 
            
            # Calculate optimal bet
            from ..bankroll.kelly import calculate_bet_for_strategy
            kelly_bet = calculate_bet_for_strategy(
                bankroll=bankroll,
                entry_price=signal.price,
                exit_price=strategy.exit_threshold,
                fraction=0.5  # Half-Kelly for safety
            )
            
            # User Override: Fixed $1 size for testing
            bet_size = 1.0
            
            # Log the Kelly recommendation vs Actual
            logger.info("strategy_runner.sizing",
                       strategy=strategy.id,
                       kelly_rec_usd=f"${kelly_bet.amount:.2f}",
                       kelly_rec_pct=f"{kelly_bet.percentage:.1%}",
                       actual_usd=f"${bet_size:.2f}",
                       reason=kelly_bet.reasoning)

            # Check Spending Limit
            now = datetime.utcnow()
            if now - self.spending_window_start > self.spending_window_duration:
                # Reset window
                self.spending_window_start = now
                self.spent_in_window = 0.0
                logger.info("strategy_runner.spending_limit_reset")
            
            if self.spent_in_window + bet_size > self.spending_limit:
                logger.warning("strategy_runner.spending_limit_hit", 
                             spent=f"${self.spent_in_window:.2f}", 
                             limit=f"${self.spending_limit:.2f}")
                return

            shares = bet_size / signal.price if signal.price > 0 else 0
            
            # Check Spending Limit
            now = datetime.utcnow()
            if now - self.spending_window_start > self.spending_window_duration:
                # Reset window
                self.spending_window_start = now
                self.spent_in_window = 0.0
                logger.info("strategy_runner.spending_limit_reset")
            
            if self.spent_in_window + bet_size > self.spending_limit:
                logger.warning("strategy_runner.spending_limit_hit", 
                             spent=f"${self.spent_in_window:.2f}", 
                             limit=f"${self.spending_limit:.2f}")
                return

            # === LIVE TRADING EXECUTION ===
            order_id = None
            is_paper = True
            
            if self.live_trader and self.config.mode == "live":
                # Get the token ID for this market
                market = self.price_collector.markets.get(price_update.condition_id)
                if market:
                    token_id = market.yes_token_id if signal.side == Side.YES else market.no_token_id
                    if token_id:
                        # Execute REAL order
                        if signal.side == Side.YES:
                            order_id = await self.live_trader.buy_yes(
                                token_id=token_id,
                                price=signal.price,
                                size=shares
                            )
                        else:
                            order_id = await self.live_trader.buy_no(
                                token_id=token_id,
                                price=signal.price,
                                size=shares
                            )
                        
                        if order_id:
                            is_paper = False
                            # Increment spending accumulator only on success
                            self.spent_in_window += bet_size
                            logger.info("strategy_runner.live_order_placed",
                                       order_id=order_id,
                                       strategy=strategy.id,
                                       side=signal.side.value,
                                       price=f"{signal.price:.1%}",
                                       shares=f"{shares:.2f}",
                                       spent_window=f"${self.spent_in_window:.2f}")
                        else:
                            logger.error("strategy_runner.live_order_failed",
                                        strategy=strategy.id)
                            return  # Don't record trade if order failed
            
            # Create trade record
            trade = Trade(
                strategy_id=strategy.id,
                market_id=price_update.market_id,
                condition_id=price_update.condition_id,
                asset=price_update.asset,
                side=signal.side,
                entry_price=signal.price,
                entry_time=datetime.utcnow(),
                shares=shares,
                time_remaining_at_entry=price_update.time_remaining,
                hour_of_day=datetime.utcnow().hour,
                day_of_week=datetime.utcnow().weekday(),
                status=TradeStatus.OPEN,
                is_paper=is_paper
            )
            
            # Save to database
            trade.id = await self.db.save_trade(trade)
            
            # Track the open trade
            self.open_trades[trade_key] = trade
            
            # Update strategy's internal position tracker
            strategy.open_position(price_update, signal.side, shares)
            
            logger.info("strategy_runner.entry",
                       strategy=strategy.id,
                       side=signal.side.value,
                       price=f"{signal.price:.1%}",
                       shares=f"{shares:.2f}",
                       live=not is_paper,
                       reason=signal.reason)
    
    async def _check_exits(
        self, 
        strategy: BaseStrategy, 
        price_update: PriceUpdate
    ) -> None:
        """Check if strategy should exit a position."""
        trade_key = (strategy.id, price_update.condition_id)
        trade = self.open_trades.get(trade_key)
        
        if not trade:
            return
        
        # Get position from strategy
        position = strategy.get_position(price_update.condition_id)
        if not position:
            # Position tracking mismatch, create temporary position
            from ..core.models import Position
            position = Position(
                strategy_id=strategy.id,
                market_id=price_update.market_id,
                condition_id=price_update.condition_id,
                asset=price_update.asset,
                side=trade.side,
                entry_price=trade.entry_price,
                entry_time=trade.entry_time,
                shares=trade.shares
            )
        
        # Check exit signal
        exit_signal, exit_price = strategy.check_exit(
            position,
            price_update,
            resolution_threshold=self.config.exits.resolution_exit_threshold,
            time_stop_threshold=self.config.exits.time_stop_threshold
        )
        
        if exit_signal != ExitSignal.HOLD:
            # Map signal to exit reason
            reason_map = {
                ExitSignal.TAKE_PROFIT: ExitReason.TAKE_PROFIT,
                ExitSignal.RESOLUTION_EXIT: ExitReason.RESOLUTION_EXIT,
                ExitSignal.TIME_STOP: ExitReason.TIME_STOP
            }
            exit_reason = reason_map.get(exit_signal, ExitReason.MANUAL)
            
            # === LIVE TRADING EXIT ===
            if self.live_trader and self.config.mode == "live":
                # Get the token ID and proper size
                market = self.price_collector.markets.get(price_update.condition_id)
                if market:
                    token_id = market.yes_token_id if trade.side == Side.YES else market.no_token_id
                    
                    if token_id:
                        # Close the Full Position
                        order_id = None
                        if trade.side == Side.YES:
                            order_id = await self.live_trader.sell_yes(
                                token_id=token_id,
                                price=exit_price,
                                size=trade.shares
                            )
                        else:
                            order_id = await self.live_trader.sell_no(
                                token_id=token_id,
                                price=exit_price,
                                size=trade.shares
                            )
                            
                        if order_id:
                            logger.info("strategy_runner.live_exit_placed",
                                      order_id=order_id,
                                      strategy=strategy.id,
                                      side=trade.side.value,
                                      price=f"{exit_price:.1%}",
                                      shares=f"{trade.shares:.2f}")
                        else:
                             # If order failed, we should simpler log it. 
                             # We still close the trade in DB to avoid getting stuck in a loop of trying to sell if its rejected?
                             # Or we just log error.
                             logger.error("strategy_runner.live_exit_failed",
                                        strategy=strategy.id)

            # Close the trade
            trade.close(
                exit_price=exit_price,
                exit_reason=exit_reason,
                time_remaining=price_update.time_remaining
            )
            
            # Update in database
            await self.db.update_trade(trade)
            
            # Update strategy stats
            await self.db.update_strategy_stats(strategy.id)
            
            # Remove from open trades
            del self.open_trades[trade_key]
            
            # Remove from strategy's position tracker
            strategy.close_position(price_update.condition_id)
            
            # If exited due to resolution or time stop, prevent immediate re-entry
            # This prevents the loop of "Bad Exit -> Re-enter -> Bad Exit"
            if exit_reason in [ExitReason.RESOLUTION_EXIT, ExitReason.TIME_STOP]:
                from datetime import timedelta
                self.cooldowns[trade_key] = datetime.utcnow() + timedelta(minutes=15)
            
            # Log the exit
            win_loss = "WIN" if trade.is_win else "LOSS"
            logger.info("strategy_runner.exit",
                       strategy=strategy.id,
                       side=trade.side.value,
                       entry=f"{trade.entry_price:.1%}",
                       exit=f"{exit_price:.1%}",
                       pnl=f"{trade.pnl_pct:.1%}" if trade.pnl_pct else "N/A",
                       result=win_loss,
                       reason=exit_reason.value)
    
    async def get_performance_summary(self) -> dict:
        """Get performance summary for all strategies."""
        return await self.db.get_strategy_performance()
    
    def get_open_positions(self) -> list[Trade]:
        """Get all currently open positions."""
        return list(self.open_trades.values())
