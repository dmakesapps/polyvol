"""
Base Strategy class.
All trading strategies inherit from this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from ..core.models import PriceUpdate, Position, Trade, Side, ExitReason


class ExitSignal(Enum):
    """Signal indicating whether to exit a position."""
    HOLD = "hold"
    TAKE_PROFIT = "take_profit"
    RESOLUTION_EXIT = "resolution_exit"
    TIME_STOP = "time_stop"


@dataclass
class EntrySignal:
    """Signal for entering a trade."""
    should_enter: bool
    side: Side
    price: float
    confidence: str = "medium"  # low, medium, high
    reason: str = ""


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    
    Strategies define:
    - Entry conditions (when to buy)
    - Exit conditions (when to sell)
    - Position sizing hints
    """
    
    def __init__(
        self,
        strategy_id: str,
        name: str,
        tier: int,
        entry_threshold: float,
        exit_threshold: float,
        direction: str = "normal"
    ):
        self.id = strategy_id
        self.name = name
        self.tier = tier
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.direction = direction  # "normal" or "fade"
        
        # Current positions per market
        self.positions: dict[str, Position] = {}
    
    @property
    def break_even_win_rate(self) -> float:
        """Calculate the break-even win rate for this strategy."""
        if self.direction == "fade":
            effective_entry = 1 - self.entry_threshold
            effective_exit = 1 - self.exit_threshold
        else:
            effective_entry = self.entry_threshold
            effective_exit = self.exit_threshold
        
        win_pct = (effective_exit - effective_entry) / effective_entry * 100
        loss_pct = 100
        
        return loss_pct / (loss_pct + win_pct)
    
    @property
    def profit_if_win(self) -> float:
        """Calculate profit percentage if trade wins."""
        if self.direction == "fade":
            effective_entry = 1 - self.entry_threshold
            effective_exit = 1 - self.exit_threshold
        else:
            effective_entry = self.entry_threshold
            effective_exit = self.exit_threshold
        
        return (effective_exit - effective_entry) / effective_entry * 100
    
    def check_entry(self, price_update: PriceUpdate) -> EntrySignal:
        """
        Check if we should enter a position.
        
        Args:
            price_update: Current price data
            
        Returns:
            EntrySignal with entry decision
        """
        # Don't enter if market is expiring soon (< 3 minutes)
        # This prevents entering trades that will immediately force a Resolution Exit (often at a loss due to spread)
        if price_update.time_remaining is not None and price_update.time_remaining < 180:
            return EntrySignal(should_enter=False, side=Side.YES, price=0, reason="Market expiring soon")

        # Don't enter if already in this market
        if price_update.condition_id in self.positions:
            return EntrySignal(should_enter=False, side=Side.YES, price=0)
        
        # For normal strategies: buy YES when price drops to entry_threshold
        # For fade strategies: buy NO when YES price rises to entry_threshold
        
        if self.direction == "fade":
            # Fade: buy NO when YES is high (e.g., 80%)
            # This means NO is at 20%, which is our effective entry
            # EXECUTION REALISM: We buy NO at the NO_ASK price
            buy_price = price_update.no_ask if price_update.no_ask else price_update.no_price
            trigger_price = price_update.yes_bid if price_update.yes_bid else price_update.yes_price
            
            # Strict Band Check: Trigger only if within 5% of threshold
            # e.g. 80% strategy only triggers in 80% - 85% range
            # Exception: For highest tier (>=90%), extend to 100% to catch extremes
            width = 0.05
            if self.entry_threshold >= 0.90:
                width = 0.10
                
            max_trigger = min(1.0, self.entry_threshold + width)
            
            if self.entry_threshold <= trigger_price < max_trigger:
                return EntrySignal(
                    should_enter=True,
                    side=Side.NO,
                    price=buy_price,
                    confidence=self._get_confidence(price_update),
                    reason=f"Fade entry: YES at {trigger_price:.1%}, buying NO at {buy_price:.1%}"
                )
        else:
            # Normal: buy YES when it drops to entry_threshold
            # EXECUTION REALISM: Buy YES at YES_ASK
            buy_price = price_update.yes_ask if price_update.yes_ask else price_update.yes_price
            
            # Strict Band Check: Entry must be within 5% of threshold
            # e.g. 20% strategy only triggers in 15% - 20% range
            min_entry = max(0, self.entry_threshold - 0.05)
            
            if min_entry < buy_price <= self.entry_threshold:
                return EntrySignal(
                    should_enter=True,
                    side=Side.YES,
                    price=buy_price,
                    confidence=self._get_confidence(price_update),
                    reason=f"Deep value entry: YES at {buy_price:.1%}"
                )
            
            # NO Side check removed for Normal strategies to prevent redundancy with Fade strategies.
            # Normal strategies (Value/Deep) are now Long-Only (Buy YES).
            pass
        
        return EntrySignal(should_enter=False, side=Side.YES, price=0)
    
    def check_exit(
        self,
        position: Position,
        price_update: PriceUpdate,
        resolution_threshold: int = 120,
        time_stop_threshold: int = 600
    ) -> tuple[ExitSignal, float]:
        """
        Check if we should exit a position.
        
        Args:
            position: Current position
            price_update: Current price data
            resolution_threshold: Seconds before resolution to exit
            time_stop_threshold: Seconds held before time stop
            
        Returns:
            Tuple of (exit signal, exit price)
        """
        # Get current price for our side
        # EXECUTION REALISM: We sell at the BID price
        if position.side == Side.YES:
            current_price = price_update.yes_bid if price_update.yes_bid else price_update.yes_price
        else:
            current_price = price_update.no_bid if price_update.no_bid else price_update.no_price
        
        # Calculate target exit price
        if self.direction == "fade":
            # For fade: we bought NO, exit when it rises to (1 - exit_threshold)
            # e.g., fade_80_70 means YES 80%->70%, NO 20%->30%
            exit_target = 1 - self.exit_threshold
        else:
            exit_target = self.exit_threshold
        
        # 1. TAKE PROFIT - hit target
        # We must have reached the exit_target AND be in profit
        # (The profit check handles spread/slippage edge cases)
        if current_price >= exit_target and current_price > position.entry_price:
            return ExitSignal.TAKE_PROFIT, current_price
        
        # 2. RESOLUTION EXIT - too close to resolution
        if price_update.time_remaining is not None:
            if price_update.time_remaining < resolution_threshold:
                return ExitSignal.RESOLUTION_EXIT, current_price
        
        # 3. TIME STOP - Removed based on user preference
        # We now hold until Take Profit or Resolution
        pass
        
        # 4. HOLD - keep position
        return ExitSignal.HOLD, current_price
    
    def _get_confidence(self, price_update: PriceUpdate) -> str:
        """Determine confidence level for entry."""
        # Ultra-deep entries (< 10%) = high confidence
        if self.entry_threshold <= 0.10:
            return "high"
        # Deep entries (10-20%) = medium confidence
        elif self.entry_threshold <= 0.20:
            return "medium"
        # Value/mid-range = low confidence
        else:
            return "low"
    
    def open_position(
        self,
        price_update: PriceUpdate,
        side: Side,
        shares: float
    ) -> Position:
        """Create and track a new position."""
        now = datetime.utcnow()
        
        entry_price = (
            price_update.yes_price if side == Side.YES
            else price_update.no_price
        )
        
        position = Position(
            strategy_id=self.id,
            market_id=price_update.market_id,
            condition_id=price_update.condition_id,
            asset=price_update.asset,
            side=side,
            entry_price=entry_price,
            entry_time=now,
            shares=shares,
            time_remaining_at_entry=price_update.time_remaining,
            hour_of_day=now.hour,
            day_of_week=now.weekday()
        )
        
        self.positions[price_update.condition_id] = position
        return position
    
    def close_position(self, condition_id: str) -> Optional[Position]:
        """Remove a position from tracking."""
        return self.positions.pop(condition_id, None)
    
    def get_position(self, condition_id: str) -> Optional[Position]:
        """Get a position by market condition ID."""
        return self.positions.get(condition_id)
    
    def has_position(self, condition_id: str) -> bool:
        """Check if we have a position in a market."""
        return condition_id in self.positions
    
    def __repr__(self) -> str:
        return f"Strategy({self.id}: {self.entry_threshold:.0%} → {self.exit_threshold:.0%})"
