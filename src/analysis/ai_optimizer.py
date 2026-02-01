"""
AI-Powered Strategy Optimizer

Uses Gemini Flash 3 via OpenRouter to analyze trading performance,
identify patterns, and suggest or apply strategy improvements.

Runs hourly to continuously optimize the bot's trading behavior.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
import structlog

from ..core.database import Database

logger = structlog.get_logger()


class AIStrategyOptimizer:
    """
    AI-powered optimizer that uses Gemini Flash 3 to analyze trades
    and suggest/implement strategy improvements.
    """
    
    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL = "google/gemini-3-flash-preview"  # Gemini Flash 3 via OpenRouter
    
    def __init__(
        self, 
        db: Database, 
        api_key: Optional[str] = None,
        auto_apply: bool = False,
        run_interval_hours: float = 1.0
    ):
        self.db = db
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.auto_apply = auto_apply
        self.run_interval_hours = run_interval_hours
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.insights_generated = 0
        
    async def start(self) -> None:
        """Start the optimizer loop."""
        if not self.api_key:
            logger.warning("ai_optimizer.no_api_key", 
                         msg="Set OPENROUTER_API_KEY to enable AI insights")
            return
            
        self._running = True
        logger.info("ai_optimizer.started", 
                   interval_hours=self.run_interval_hours,
                   auto_apply=self.auto_apply)
        
        # Run first analysis immediately
        await self._run_analysis()
        
        # Then run on schedule
        self._task = asyncio.create_task(self._run_loop())
        
    async def stop(self) -> None:
        """Stop the optimizer loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ai_optimizer.stopped")
        
    async def _run_loop(self) -> None:
        """Main optimizer loop."""
        while self._running:
            await asyncio.sleep(self.run_interval_hours * 3600)  # Convert to seconds
            if self._running:
                await self._run_analysis()
                
    async def _run_analysis(self) -> None:
        """Run a complete analysis cycle."""
        try:
            logger.info("ai_optimizer.analysis_started")
            
            # 1. Gather performance data
            performance_data = await self._gather_performance_data()
            
            # 2. Generate AI insights
            insights = await self._generate_insights(performance_data)
            
            if insights:
                # 3. Save insights to database
                await self._save_insights(insights)
                
                # 4. Apply safe improvements if enabled
                if self.auto_apply:
                    await self._apply_safe_improvements(insights)
                    
            self.last_run = datetime.utcnow()
            self.insights_generated += 1
            
            logger.info("ai_optimizer.analysis_completed",
                       insights_count=len(insights) if insights else 0)
                       
        except Exception as e:
            logger.error("ai_optimizer.analysis_failed", error=str(e))
            
    async def _gather_performance_data(self) -> Dict[str, Any]:
        """Gather comprehensive performance data for analysis."""
        
        # Get strategy performance
        strategy_perf = await self.db.get_strategy_performance()
        
        # Get recent trades (last 24 hours)
        recent_trades = await self._get_recent_trades(hours=24)
        
        # Get all-time closed trades for pattern analysis
        all_trades = await self._get_all_closed_trades(limit=500)
        
        # Calculate derived metrics
        metrics = self._calculate_metrics(recent_trades, all_trades)
        
        return {
            "strategies": strategy_perf,
            "recent_trades_24h": self._trades_to_summary(recent_trades),
            "all_trades_summary": self._trades_to_summary(all_trades),
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def _get_recent_trades(self, hours: int = 24) -> List[Dict]:
        """Get trades from the last N hours."""
        cursor = await self.db._conn.execute("""
            SELECT * FROM trades 
            WHERE entry_time > datetime('now', ?)
            ORDER BY entry_time DESC
        """, (f'-{hours} hours',))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
        
    async def _get_all_closed_trades(self, limit: int = 500) -> List[Dict]:
        """Get all closed trades for pattern analysis."""
        cursor = await self.db._conn.execute("""
            SELECT * FROM trades 
            WHERE status = 'closed'
            ORDER BY exit_time DESC
            LIMIT ?
        """, (limit,))
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
        
    def _trades_to_summary(self, trades: List[Dict]) -> Dict:
        """Convert trades list to summary stats."""
        if not trades:
            return {"count": 0}
            
        wins = sum(1 for t in trades if t.get('is_win'))
        losses = sum(1 for t in trades if t.get('is_win') == 0)
        total_pnl = sum(t.get('pnl', 0) or 0 for t in trades)
        
        # Group by strategy
        by_strategy = {}
        for t in trades:
            sid = t.get('strategy_id', 'unknown')
            if sid not in by_strategy:
                by_strategy[sid] = {"wins": 0, "losses": 0, "pnl": 0}
            if t.get('is_win'):
                by_strategy[sid]["wins"] += 1
            elif t.get('is_win') == 0:
                by_strategy[sid]["losses"] += 1
            by_strategy[sid]["pnl"] += t.get('pnl', 0) or 0
            
        # Group by asset
        by_asset = {}
        for t in trades:
            asset = t.get('asset', 'unknown')
            if asset not in by_asset:
                by_asset[asset] = {"wins": 0, "losses": 0, "pnl": 0}
            if t.get('is_win'):
                by_asset[asset]["wins"] += 1
            elif t.get('is_win') == 0:
                by_asset[asset]["losses"] += 1
            by_asset[asset]["pnl"] += t.get('pnl', 0) or 0
            
        # Group by hour of day
        by_hour = {}
        for t in trades:
            hour = t.get('hour_of_day')
            if hour is not None:
                if hour not in by_hour:
                    by_hour[hour] = {"wins": 0, "losses": 0, "pnl": 0}
                if t.get('is_win'):
                    by_hour[hour]["wins"] += 1
                elif t.get('is_win') == 0:
                    by_hour[hour]["losses"] += 1
                by_hour[hour]["pnl"] += t.get('pnl', 0) or 0
                
        # Exit reasons
        exit_reasons = {}
        for t in trades:
            reason = t.get('exit_reason', 'none')
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
            
        return {
            "count": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else None,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / len(trades), 2) if trades else 0,
            "by_strategy": by_strategy,
            "by_asset": by_asset,
            "by_hour": by_hour,
            "exit_reasons": exit_reasons
        }
        
    def _calculate_metrics(self, recent: List[Dict], all_trades: List[Dict]) -> Dict:
        """Calculate advanced metrics for AI analysis."""
        metrics = {}
        
        # Streak analysis
        if all_trades:
            current_streak = 0
            streak_type = None
            for t in all_trades:
                if t.get('is_win') is None:
                    continue
                if streak_type is None:
                    streak_type = 'win' if t['is_win'] else 'loss'
                    current_streak = 1
                elif (streak_type == 'win') == bool(t['is_win']):
                    current_streak += 1
                else:
                    break
            metrics['current_streak'] = {"type": streak_type, "count": current_streak}
            
        # Time-based patterns
        if all_trades:
            # Best/worst hours
            hour_stats = {}
            for t in all_trades:
                h = t.get('hour_of_day')
                if h is not None:
                    if h not in hour_stats:
                        hour_stats[h] = {'wins': 0, 'total': 0}
                    hour_stats[h]['total'] += 1
                    if t.get('is_win'):
                        hour_stats[h]['wins'] += 1
                        
            if hour_stats:
                hour_wr = {h: s['wins']/s['total'] for h, s in hour_stats.items() if s['total'] >= 3}
                if hour_wr:
                    best_hour = max(hour_wr, key=hour_wr.get)
                    worst_hour = min(hour_wr, key=hour_wr.get)
                    metrics['best_hour'] = {"hour": best_hour, "win_rate": round(hour_wr[best_hour]*100, 1)}
                    metrics['worst_hour'] = {"hour": worst_hour, "win_rate": round(hour_wr[worst_hour]*100, 1)}
                    
        # Entry price distribution
        if all_trades:
            entry_prices = [t['entry_price'] for t in all_trades if t.get('entry_price')]
            if entry_prices:
                metrics['avg_entry_price'] = round(sum(entry_prices) / len(entry_prices), 3)
                
        # Win rate by entry price range
        price_buckets = {
            "ultra_deep_0_10": {"wins": 0, "total": 0},
            "deep_10_20": {"wins": 0, "total": 0},
            "value_20_30": {"wins": 0, "total": 0},
            "mid_30_50": {"wins": 0, "total": 0},
            "high_50_plus": {"wins": 0, "total": 0}
        }
        for t in all_trades:
            p = t.get('entry_price', 0)
            if p <= 0.10:
                bucket = "ultra_deep_0_10"
            elif p <= 0.20:
                bucket = "deep_10_20"
            elif p <= 0.30:
                bucket = "value_20_30"
            elif p <= 0.50:
                bucket = "mid_30_50"
            else:
                bucket = "high_50_plus"
            price_buckets[bucket]['total'] += 1
            if t.get('is_win'):
                price_buckets[bucket]['wins'] += 1
                
        metrics['win_rate_by_price_bucket'] = {
            k: round(v['wins']/v['total']*100, 1) if v['total'] > 0 else None
            for k, v in price_buckets.items()
        }
        
        return metrics
        
    async def _generate_insights(self, data: Dict) -> List[Dict]:
        """Use Gemini Flash 3 to generate actionable insights."""
        
        prompt = self._build_analysis_prompt(data)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.OPENROUTER_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://polyvol.trading",
                        "X-Title": "PolyVol AI Optimizer"
                    },
                    json={
                        "model": self.MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": self._get_system_prompt()
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,  # Lower for more consistent analysis
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code != 200:
                    logger.error("ai_optimizer.api_error", 
                               status=response.status_code,
                               body=response.text[:500])
                    return []
                    
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse the structured response
                insights = self._parse_insights(content)
                
                logger.info("ai_optimizer.insights_generated", 
                          count=len(insights),
                          model=self.MODEL)
                          
                return insights
                
        except Exception as e:
            logger.error("ai_optimizer.generation_failed", error=str(e))
            return []
            
    def _get_system_prompt(self) -> str:
        """System prompt for the AI optimizer."""
        return """You are an AI trading strategy optimizer for a Polymarket volatility bot.

Your job is to analyze trading performance data and provide actionable insights.

The bot trades 15-minute binary option markets on cryptocurrency prices.
It uses multiple strategies with different entry/exit thresholds:
- "Deep value" strategies: Buy when YES price is 5-20¢, sell at 10-30¢
- "Fade" strategies: Buy NO when YES is at 80-90¢ (contrarian)

KEY METRICS TO OPTIMIZE:
1. Win rate (target: 60%+ for profitability)
2. Average P&L per trade
3. Exit timing (before resolution vs take profit)
4. Asset selection (BTC, ETH, SOL, XRP performance)
5. Time-of-day patterns

RESPONSE FORMAT (REQUIRED):
Return ONLY a JSON array of insight objects. Each insight must have:
{
  "type": "observation" | "recommendation" | "warning" | "auto_fix",
  "category": "strategy" | "timing" | "asset" | "risk" | "general",
  "priority": "high" | "medium" | "low",
  "title": "Brief title",
  "description": "Detailed explanation",
  "action": "Specific action to take (if applicable)",
  "auto_apply": true | false  // Only true for safe, reversible changes
}

Be specific and data-driven. Reference actual numbers from the data provided."""
        
    def _build_analysis_prompt(self, data: Dict) -> str:
        """Build the analysis prompt with performance data."""
        return f"""Analyze this trading bot performance data and provide insights:

## Strategy Performance
{json.dumps(data['strategies'], indent=2)}

## Last 24 Hours Summary
{json.dumps(data['recent_trades_24h'], indent=2)}

## All-Time Trade Summary (Last 500 trades)
{json.dumps(data['all_trades_summary'], indent=2)}

## Advanced Metrics
{json.dumps(data['metrics'], indent=2)}

Based on this data, provide:
1. Key observations about current performance
2. Specific recommendations to improve win rate or profitability  
3. Any warnings about concerning patterns
4. Optional auto-fix suggestions (only for safe, reversible changes)

Return your analysis as a JSON array of insight objects."""

    def _parse_insights(self, content: str) -> List[Dict]:
        """Parse AI response into structured insights."""
        try:
            # Try to find JSON in the response
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            insights = json.loads(content.strip())
            
            if isinstance(insights, list):
                return insights
            elif isinstance(insights, dict) and 'insights' in insights:
                return insights['insights']
            else:
                return [insights]
                
        except json.JSONDecodeError as e:
            logger.warning("ai_optimizer.parse_failed", 
                         error=str(e),
                         content_preview=content[:200])
            # Return raw content as single insight
            return [{
                "type": "observation",
                "category": "general",
                "priority": "medium",
                "title": "AI Analysis",
                "description": content[:500],
                "action": None,
                "auto_apply": False
            }]
            
    async def _save_insights(self, insights: List[Dict]) -> None:
        """Save insights to the database."""
        for insight in insights:
            try:
                await self.db._conn.execute("""
                    INSERT INTO insights (
                        insight_type, content, confidence, 
                        tested, validated, llm_model, metadata
                    ) VALUES (?, ?, ?, 0, 0, ?, ?)
                """, (
                    insight.get('type', 'observation'),
                    json.dumps(insight),
                    1.0 if insight.get('priority') == 'high' else 0.7,
                    self.MODEL,
                    json.dumps({
                        "category": insight.get('category'),
                        "priority": insight.get('priority'),
                        "auto_apply": insight.get('auto_apply', False)
                    })
                ))
            except Exception as e:
                logger.error("ai_optimizer.save_insight_failed", error=str(e))
                
        await self.db._conn.commit()
        logger.info("ai_optimizer.insights_saved", count=len(insights))
        
    async def _apply_safe_improvements(self, insights: List[Dict]) -> None:
        """Apply safe, reversible improvements automatically."""
        for insight in insights:
            if not insight.get('auto_apply'):
                continue
                
            try:
                action = insight.get('action', '')
                category = insight.get('category', '')
                title = insight.get('title', '').lower()
                
                # 1. Strategy Management (Disable poor performers)
                if category == 'strategy' and ('disable' in action.lower() or 'stop' in action.lower()):
                    # Extract strategy ID from action or title
                    import re
                    match = re.search(r'strategy ([a-z0-9_]+)', f"{action} {title}")
                    if match:
                        strategy_id = match.group(1)
                        logger.info("ai_optimizer.disabling_strategy", 
                                  strategy=strategy_id, 
                                  reason=insight.get('description'))
                        
                        await self.db._conn.execute(
                            "UPDATE strategies SET status = 'disabled' WHERE id = ?",
                            (strategy_id,)
                        )
                        await self.db._conn.commit()
                        
                # 2. Strategy Management (Enable good performers if they were disabled)
                elif category == 'strategy' and ('enable' in action.lower() or 'promote' in action.lower()):
                    import re
                    match = re.search(r'strategy ([a-z0-9_]+)', f"{action} {title}")
                    if match:
                        strategy_id = match.group(1)
                        logger.info("ai_optimizer.enabling_strategy", 
                                  strategy=strategy_id, 
                                  reason=insight.get('description'))
                        
                        await self.db._conn.execute(
                            "UPDATE strategies SET status = 'enabled' WHERE id = ?",
                            (strategy_id,)
                        )
                        await self.db._conn.commit()

                # 3. Timing/Risk Adjustments (Placeholder for future implementation)
                elif category == 'timing' and 'avoid hour' in action.lower():
                    logger.info("ai_optimizer.would_apply_timing", 
                               action=action,
                               note="Timing adjustments not yet implemented in core")
                              
                else:
                    logger.info("ai_optimizer.skipped_auto_apply",
                              action=action,
                              reason="Change type not yet automated")
                              
            except Exception as e:
                logger.error("ai_optimizer.auto_apply_failed", 
                           error=str(e),
                           insight=insight.get('title'))
                           
    async def get_latest_insights(self, limit: int = 10) -> List[Dict]:
        """Get the most recent insights from the database."""
        cursor = await self.db._conn.execute("""
            SELECT content, created_at FROM insights
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = await cursor.fetchall()
        insights = []
        for row in rows:
            try:
                insight = json.loads(row['content'])
                insight['created_at'] = row['created_at']
                insights.append(insight)
            except:
                pass
        return insights
        
    async def run_now(self) -> List[Dict]:
        """Manually trigger an analysis and return insights."""
        if not self.api_key:
            return [{"error": "No OPENROUTER_API_KEY configured"}]
            
        data = await self._gather_performance_data()
        insights = await self._generate_insights(data)
        
        if insights:
            await self._save_insights(insights)
            
        return insights


# Convenience function to create and start optimizer
async def create_optimizer(db: Database) -> AIStrategyOptimizer:
    """Create and start the AI optimizer."""
    optimizer = AIStrategyOptimizer(
        db=db,
        auto_apply=False,  # Start conservative
        run_interval_hours=1.0
    )
    await optimizer.start()
    return optimizer
