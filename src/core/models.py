"""
Data models for the trading system.
Uses Pydantic for validation and serialization.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Side(str, Enum):
    """Trading side."""
    YES = "YES"
    NO = "NO"


class TradeStatus(str, Enum):
    """Trade status."""
    OPEN = "open"
    CLOSED = "closed"


class ExitReason(str, Enum):
    """Why a trade was exited."""
    TAKE_PROFIT = "TAKE_PROFIT"
    RESOLUTION_EXIT = "RESOLUTION_EXIT"
    TIME_STOP = "TIME_STOP"
    RESOLUTION_WIN = "RESOLUTION_WIN"
    RESOLUTION_LOSS = "RESOLUTION_LOSS"
    MANUAL = "MANUAL"


class StrategyStatus(str, Enum):
    """Strategy status levels."""
    TESTING = "testing"
    ACTIVE = "active"
    PROMISING = "promising"
    CHAMPION = "champion"
    UNDERPERFORMING = "underperforming"
    RETIRED = "retired"


class PriceUpdate(BaseModel):
    """A single price update from the market."""
    market_id: str
    condition_id: str
    asset: str  # BTC, ETH, etc.
    yes_price: float
    no_price: float
    time_remaining: Optional[float] = None  # Seconds until resolution
    volume: Optional[float] = None
    liquidity: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # Market depth for realistic simulation
    yes_bid: Optional[float] = None
    yes_ask: Optional[float] = None
    no_bid: Optional[float] = None
    no_ask: Optional[float] = None


class Market(BaseModel):
    """A Polymarket market."""
    id: str
    condition_id: str
    question: str
    asset: str  # BTC, ETH, etc.
    end_time: datetime
    yes_price: float = 0.50
    no_price: float = 0.50
    volume: float = 0.0
    liquidity: float = 0.0
    is_active: bool = True
    # CLOB token IDs for real-time orderbook prices
    yes_token_id: Optional[str] = None
    no_token_id: Optional[str] = None
    
    # Real-time Order Book Data
    yes_bid: Optional[float] = None
    yes_ask: Optional[float] = None
    no_bid: Optional[float] = None
    no_ask: Optional[float] = None


class Position(BaseModel):
    """An open position in a market."""
    id: Optional[int] = None
    strategy_id: str
    market_id: str
    condition_id: str
    asset: str
    side: Side
    entry_price: float
    entry_time: datetime
    shares: float
    
    # Context at entry
    time_remaining_at_entry: Optional[float] = None
    price_1min_ago: Optional[float] = None
    price_5min_ago: Optional[float] = None
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None


class Trade(BaseModel):
    """A completed trade (closed position)."""
    id: Optional[int] = None
    strategy_id: str
    market_id: str
    condition_id: str
    asset: str
    side: Side
    
    # Entry
    entry_price: float
    entry_time: datetime
    shares: float
    
    # Exit
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    
    # Outcome
    pnl: Optional[float] = None  # Profit/loss in dollars
    pnl_pct: Optional[float] = None  # Profit/loss percentage
    is_win: Optional[bool] = None
    
    # Context
    time_remaining_at_entry: Optional[float] = None
    time_remaining_at_exit: Optional[float] = None
    price_1min_ago: Optional[float] = None
    price_5min_ago: Optional[float] = None
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    market_volatility: Optional[float] = None
    
    # Metadata
    status: TradeStatus = TradeStatus.OPEN
    is_paper: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def close(
        self,
        exit_price: float,
        exit_reason: ExitReason,
        time_remaining: Optional[float] = None
    ) -> None:
        """Close the trade and calculate P&L."""
        self.exit_price = exit_price
        self.exit_time = datetime.utcnow()
        self.exit_reason = exit_reason
        self.time_remaining_at_exit = time_remaining
        self.status = TradeStatus.CLOSED
        
        # Calculate P&L
        # For YES side: profit = (exit - entry) / entry
        # For NO side: same calculation but we bought the NO side
        if self.side == Side.YES:
            self.pnl_pct = (exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl_pct = (exit_price - self.entry_price) / self.entry_price
        
        self.pnl = self.shares * self.entry_price * self.pnl_pct
        
        # Determine if win (hit target or resolution win)
        self.is_win = exit_reason in [ExitReason.TAKE_PROFIT, ExitReason.RESOLUTION_WIN]


class Strategy(BaseModel):
    """A trading strategy configuration and stats."""
    id: str
    name: str
    tier: int
    entry_threshold: float
    exit_threshold: float
    direction: str = "normal"  # normal or fade
    
    # Lineage
    generation: int = 0
    parent_id: Optional[str] = None
    
    # Status
    status: StrategyStatus = StrategyStatus.TESTING
    
    # Performance (cached)
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: Optional[float] = None
    total_pnl: float = 0.0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    retired_at: Optional[datetime] = None
    
    @property
    def break_even_win_rate(self) -> float:
        """Calculate the break-even win rate for this strategy."""
        # Win = (exit - entry) / entry * 100
        # Loss = -100% (goes to 0)
        if self.direction == "fade":
            # Fade: we buy the opposite side
            effective_entry = 1 - self.entry_threshold
            effective_exit = 1 - self.exit_threshold
        else:
            effective_entry = self.entry_threshold
            effective_exit = self.exit_threshold
        
        win_pct = (effective_exit - effective_entry) / effective_entry * 100
        loss_pct = 100  # Total loss if goes to 0
        
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


class Snapshot(BaseModel):
    """Performance snapshot for a time period."""
    id: Optional[int] = None
    strategy_id: str
    period_start: datetime
    period_end: datetime
    period_type: str  # hour, day, week
    
    # Metrics
    trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: Optional[float] = None
    total_pnl: float = 0.0
    avg_pnl: Optional[float] = None
    
    # Breakdown
    take_profits: int = 0
    resolution_exits: int = 0
    time_stops: int = 0
    
    # Risk
    max_drawdown: Optional[float] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
