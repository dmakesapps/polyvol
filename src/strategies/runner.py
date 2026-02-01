"""
Multi-Strategy Runner.
Runs all strategies simultaneously against live price data.
Manages paper trades and tracks performance.
"""
import asyncio
from datetime import datetime
from typing import Optional
import structlog

from ..core.config import get_config, StrategyConfig
from ..core.database import Database
from ..core.models import (
    Trade, Strategy as StrategyModel, PriceUpdate, 
    Side, TradeStatus, ExitReason, StrategyStatus
)
from ..collection.price_collector import PriceCollector
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
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        
        logger.info("strategy_runner.started", 
                   strategies=len(self.strategies))
    
    async def stop(self) -> None:
        """Stop the strategy runner."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("strategy_runner.stopped")
    
    async def _load_strategies(self) -> None:
        """Load and initialize strategies from config."""
        for strat_config in self.config.strategies:
            if not strat_config.enabled:
                continue
            
            # Create strategy instance
            strategy = create_strategy({
                "id": strat_config.id,
                "entry": strat_config.entry,
                "exit": strat_config.exit,
                "tier": strat_config.tier,
                "direction": strat_config.direction
            })
            
            self.strategies[strategy.id] = strategy
            
            # Save strategy to database
            db_strategy = StrategyModel(
                id=strategy.id,
                name=strategy.name,
                tier=strategy.tier,
                entry_threshold=strategy.entry_threshold,
                exit_threshold=strategy.exit_threshold,
                direction=strategy.direction,
                status=StrategyStatus.TESTING
            )
            await self.db.save_strategy(db_strategy)
            
            logger.info("strategy_runner.strategy_loaded",
                       id=strategy.id,
                       entry=strategy.entry_threshold,
                       exit=strategy.exit_threshold,
                       break_even_wr=f"{strategy.break_even_win_rate:.1%}")
    
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
        
        # Check entry signal
        signal = strategy.check_entry(price_update)
        
        if signal.should_enter:
            # Calculate position size (paper trading uses fixed $10)
            bet_size = 10.0  # $10 per trade for paper trading
            shares = bet_size / signal.price
            
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
                is_paper=True
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
