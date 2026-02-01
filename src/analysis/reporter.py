"""
Performance Reporter.
Generates human-readable reports and summaries.
"""
from datetime import datetime
from typing import Optional
import structlog

from ..core.database import Database
from .metrics import MetricsCalculator


logger = structlog.get_logger()


class Reporter:
    """Generate performance reports."""
    
    def __init__(self, db: Database):
        self.db = db
        self.metrics = MetricsCalculator(db)
    
    async def generate_summary(self, hours: Optional[int] = None) -> str:
        """
        Generate a text summary of all strategy performance.
        
        Args:
            hours: Optional time window
            
        Returns:
            Formatted text report
        """
        all_metrics = await self.metrics.get_all_strategies_metrics(hours)
        
        lines = [
            "=" * 60,
            "POLYMARKET VOLATILITY BOT - PERFORMANCE REPORT",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"Period: {'Last ' + str(hours) + ' hours' if hours else 'All time'}",
            "=" * 60,
            ""
        ]
        
        # Summary stats
        total_trades = sum(m["total_trades"] for m in all_metrics)
        total_wins = sum(m["wins"] for m in all_metrics)
        overall_wr = total_wins / total_trades if total_trades > 0 else 0
        total_pnl = sum(m["total_pnl"] for m in all_metrics)
        
        lines.extend([
            "OVERALL SUMMARY",
            "-" * 40,
            f"Total Trades: {total_trades}",
            f"Overall Win Rate: {overall_wr:.1%}",
            f"Total P&L: ${total_pnl:.2f}",
            ""
        ])
        
        # Strategy breakdown
        lines.extend([
            "STRATEGY PERFORMANCE",
            "-" * 40,
            f"{'Strategy':<15} {'Tier':>4} {'Trades':>7} {'WR':>7} {'P&L':>10} {'Status':>12}",
            "-" * 60
        ])
        
        for m in all_metrics:
            # Determine status
            if m["total_trades"] < 50:
                status = "Testing"
            elif m["win_rate"] >= 0.75:
                status = "⭐ CHAMPION"
            elif m["win_rate"] >= 0.70:
                status = "Promising"
            elif m["win_rate"] >= m.get("break_even_wr", 0.5):
                status = "Profitable"
            else:
                status = "⚠️ Review"
            
            lines.append(
                f"{m['strategy_id']:<15} "
                f"{m.get('tier', '?'):>4} "
                f"{m['total_trades']:>7} "
                f"{m['win_rate_pct']:>7} "
                f"${m['total_pnl']:>9.2f} "
                f"{status:>12}"
            )
        
        lines.extend(["", "=" * 60])
        
        # Top performers
        top = [m for m in all_metrics if m["total_trades"] >= 50]
        top = sorted(top, key=lambda x: x["win_rate"], reverse=True)[:5]
        
        if top:
            lines.extend([
                "",
                "TOP PERFORMERS (50+ trades)",
                "-" * 40
            ])
            for i, m in enumerate(top, 1):
                lines.append(
                    f"{i}. {m['strategy_id']}: {m['win_rate_pct']} WR, "
                    f"${m['total_pnl']:.2f} P&L, "
                    f"{m['total_trades']} trades"
                )
        
        # Champions (75%+ WR)
        champions = [m for m in all_metrics if m["total_trades"] >= 50 and m["win_rate"] >= 0.75]
        
        if champions:
            lines.extend([
                "",
                "🏆 CHAMPIONS (75%+ Win Rate with 50+ trades)",
                "-" * 40
            ])
            for m in champions:
                lines.append(
                    f"⭐ {m['strategy_id']}: {m['win_rate_pct']} WR, "
                    f"Profit Factor: {m['profit_factor']:.2f}"
                )
        else:
            lines.extend([
                "",
                "🎯 GOAL: Achieve 75%+ Win Rate",
                "-" * 40,
                "No strategies have reached champion status yet.",
                "Keep collecting data - need 50+ trades per strategy."
            ])
        
        lines.extend(["", "=" * 60])
        
        return "\n".join(lines)
    
    async def generate_json_report(self, hours: Optional[int] = None) -> dict:
        """Generate a JSON report for LLM consumption."""
        all_metrics = await self.metrics.get_all_strategies_metrics(hours)
        
        # Get recent trades for context
        recent_trades = []
        strategies = await self.db.get_active_strategies()
        for strat in strategies[:5]:  # Top 5 by recent activity
            trades = await self.db.get_trades_by_strategy(strat.id, limit=10)
            for t in trades:
                if t.exit_price:
                    recent_trades.append({
                        "strategy": t.strategy_id,
                        "entry": t.entry_price,
                        "exit": t.exit_price,
                        "pnl_pct": f"{t.pnl_pct:.1%}" if t.pnl_pct else None,
                        "result": "WIN" if t.is_win else "LOSS",
                        "reason": t.exit_reason.value if t.exit_reason else None
                    })
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "period_hours": hours,
            "summary": {
                "total_strategies": len(all_metrics),
                "total_trades": sum(m["total_trades"] for m in all_metrics),
                "overall_win_rate": sum(m["wins"] for m in all_metrics) / max(1, sum(m["total_trades"] for m in all_metrics)),
                "total_pnl": sum(m["total_pnl"] for m in all_metrics)
            },
            "strategies": all_metrics,
            "recent_trades": recent_trades[:50],
            "champions": [
                m["strategy_id"] for m in all_metrics 
                if m["total_trades"] >= 50 and m["win_rate"] >= 0.75
            ]
        }
    
    async def print_quick_status(self) -> None:
        """Print a quick status update to the console."""
        all_metrics = await self.metrics.get_all_strategies_metrics()
        
        total_trades = sum(m["total_trades"] for m in all_metrics)
        total_wins = sum(m["wins"] for m in all_metrics)
        overall_wr = total_wins / total_trades if total_trades > 0 else 0
        
        # Find best performer
        with_trades = [m for m in all_metrics if m["total_trades"] >= 10]
        best = max(with_trades, key=lambda x: x["win_rate"]) if with_trades else None
        
        logger.info(
            "status_update",
            total_trades=total_trades,
            overall_win_rate=f"{overall_wr:.1%}",
            best_strategy=best["strategy_id"] if best else None,
            best_wr=best["win_rate_pct"] if best else None,
            strategies_active=len(all_metrics)
        )
