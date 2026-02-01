"""
Performance metrics calculations.
Computes win rate, profit factor, drawdown, and other statistics.
"""
from datetime import datetime, timedelta
from typing import Optional
import structlog

from ..core.database import Database
from ..core.models import Trade, ExitReason


logger = structlog.get_logger()


class MetricsCalculator:
    """Calculate performance metrics for strategies."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_strategy_metrics(
        self, 
        strategy_id: str,
        hours: Optional[int] = None
    ) -> dict:
        """
        Calculate comprehensive metrics for a strategy.
        
        Args:
            strategy_id: Strategy to analyze
            hours: Optional time window in hours
            
        Returns:
            Dict with all metrics
        """
        trades = await self.db.get_trades_by_strategy(strategy_id, limit=1000)
        
        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            trades = [t for t in trades if t.entry_time >= cutoff]
        
        # Only closed trades for metrics
        closed = [t for t in trades if t.exit_price is not None]
        
        if not closed:
            return self._empty_metrics(strategy_id)
        
        # Basic counts
        total = len(closed)
        wins = sum(1 for t in closed if t.is_win)
        losses = total - wins
        
        # Win rate
        win_rate = wins / total if total > 0 else 0
        
        # P&L
        total_pnl = sum(t.pnl or 0 for t in closed)
        gross_profit = sum(t.pnl for t in closed if t.pnl and t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in closed if t.pnl and t.pnl < 0))
        avg_pnl = total_pnl / total if total > 0 else 0
        
        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # By exit reason
        take_profits = sum(1 for t in closed if t.exit_reason == ExitReason.TAKE_PROFIT)
        resolution_exits = sum(1 for t in closed if t.exit_reason == ExitReason.RESOLUTION_EXIT)
        time_stops = sum(1 for t in closed if t.exit_reason == ExitReason.TIME_STOP)
        
        # Win streaks
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        temp_win = 0
        temp_loss = 0
        
        for t in sorted(closed, key=lambda x: x.entry_time):
            if t.is_win:
                temp_win += 1
                temp_loss = 0
                max_win_streak = max(max_win_streak, temp_win)
            else:
                temp_loss += 1
                temp_win = 0
                max_loss_streak = max(max_loss_streak, temp_loss)
        
        # Drawdown
        max_drawdown = self._calculate_max_drawdown(closed)
        
        # Average hold time
        hold_times = []
        for t in closed:
            if t.exit_time:
                hold_time = (t.exit_time - t.entry_time).total_seconds()
                hold_times.append(hold_time)
        avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
        
        return {
            "strategy_id": strategy_id,
            "period_hours": hours,
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "win_rate_pct": f"{win_rate * 100:.1f}%",
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "take_profits": take_profits,
            "resolution_exits": resolution_exits,
            "time_stops": time_stops,
            "take_profit_rate": take_profits / total if total > 0 else 0,
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
            "max_drawdown": max_drawdown,
            "avg_hold_time_seconds": avg_hold_time
        }
    
    async def get_all_strategies_metrics(self, hours: Optional[int] = None) -> list[dict]:
        """Get metrics for all strategies."""
        strategies = await self.db.get_active_strategies()
        
        results = []
        for strat in strategies:
            metrics = await self.get_strategy_metrics(strat.id, hours)
            metrics["tier"] = strat.tier
            metrics["entry"] = strat.entry_threshold
            metrics["exit"] = strat.exit_threshold
            metrics["break_even_wr"] = strat.break_even_win_rate
            results.append(metrics)
        
        # Sort by win rate descending
        results.sort(key=lambda x: x["win_rate"], reverse=True)
        
        return results
    
    async def get_hourly_breakdown(self, strategy_id: str) -> dict:
        """Analyze performance by hour of day."""
        trades = await self.db.get_trades_by_strategy(strategy_id, limit=1000)
        closed = [t for t in trades if t.exit_price is not None]
        
        by_hour = {}
        for hour in range(24):
            hour_trades = [t for t in closed if t.hour_of_day == hour]
            total = len(hour_trades)
            wins = sum(1 for t in hour_trades if t.is_win)
            by_hour[hour] = {
                "trades": total,
                "wins": wins,
                "win_rate": wins / total if total > 0 else None
            }
        
        return by_hour
    
    async def get_entry_price_breakdown(self, strategy_id: str) -> dict:
        """Analyze performance by entry price ranges."""
        trades = await self.db.get_trades_by_strategy(strategy_id, limit=1000)
        closed = [t for t in trades if t.exit_price is not None]
        
        ranges = [
            (0.00, 0.10, "0-10%"),
            (0.10, 0.20, "10-20%"),
            (0.20, 0.30, "20-30%"),
            (0.30, 0.40, "30-40%"),
            (0.40, 0.50, "40-50%"),
            (0.50, 0.60, "50-60%"),
            (0.60, 0.70, "60-70%"),
            (0.70, 0.80, "70-80%"),
            (0.80, 0.90, "80-90%"),
            (0.90, 1.00, "90-100%")
        ]
        
        by_range = {}
        for low, high, label in ranges:
            range_trades = [
                t for t in closed 
                if low <= t.entry_price < high
            ]
            total = len(range_trades)
            wins = sum(1 for t in range_trades if t.is_win)
            by_range[label] = {
                "trades": total,
                "wins": wins,
                "win_rate": wins / total if total > 0 else None
            }
        
        return by_range
    
    def _calculate_max_drawdown(self, trades: list[Trade]) -> float:
        """Calculate maximum drawdown from trade sequence."""
        if not trades:
            return 0.0
        
        # Sort by entry time
        sorted_trades = sorted(trades, key=lambda t: t.entry_time)
        
        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0
        
        for trade in sorted_trades:
            cumulative_pnl += trade.pnl or 0
            peak = max(peak, cumulative_pnl)
            drawdown = (peak - cumulative_pnl) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _empty_metrics(self, strategy_id: str) -> dict:
        """Return empty metrics for a strategy with no trades."""
        return {
            "strategy_id": strategy_id,
            "period_hours": None,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "win_rate_pct": "0.0%",
            "total_pnl": 0,
            "avg_pnl": 0,
            "gross_profit": 0,
            "gross_loss": 0,
            "profit_factor": 0,
            "take_profits": 0,
            "resolution_exits": 0,
            "time_stops": 0,
            "take_profit_rate": 0,
            "max_win_streak": 0,
            "max_loss_streak": 0,
            "max_drawdown": 0,
            "avg_hold_time_seconds": 0
        }
