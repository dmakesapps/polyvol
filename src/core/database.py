"""
SQLite database operations.
Handles all data persistence for prices, trades, strategies, and snapshots.
"""
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from .models import (
    Trade, Strategy, PriceUpdate, Snapshot,
    TradeStatus, StrategyStatus, ExitReason, Side
)


class Database:
    """Async SQLite database wrapper."""
    
    def __init__(self, db_path: str = "data/evolution.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Connect to the database and initialize tables."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        
        await self._init_tables()
    
    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    async def _init_tables(self) -> None:
        """Create database tables if they don't exist."""
        await self._conn.executescript("""
            -- Price history
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                condition_id TEXT NOT NULL,
                asset TEXT NOT NULL,
                yes_price REAL NOT NULL,
                no_price REAL NOT NULL,
                time_remaining REAL,
                volume REAL,
                liquidity REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_prices_market ON prices(market_id);
            CREATE INDEX IF NOT EXISTS idx_prices_time ON prices(timestamp);
            CREATE INDEX IF NOT EXISTS idx_prices_asset ON prices(asset);
            
            -- Trades
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                market_id TEXT NOT NULL,
                condition_id TEXT NOT NULL,
                asset TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP,
                shares REAL NOT NULL,
                pnl REAL,
                pnl_pct REAL,
                is_win INTEGER,
                exit_reason TEXT,
                time_remaining_at_entry REAL,
                time_remaining_at_exit REAL,
                price_1min_ago REAL,
                price_5min_ago REAL,
                hour_of_day INTEGER,
                day_of_week INTEGER,
                market_volatility REAL,
                status TEXT DEFAULT 'open',
                is_paper INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_id);
            CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
            CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(entry_time);
            
            -- Strategies
            CREATE TABLE IF NOT EXISTS strategies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tier INTEGER,
                entry_threshold REAL NOT NULL,
                exit_threshold REAL NOT NULL,
                direction TEXT DEFAULT 'normal',
                generation INTEGER DEFAULT 0,
                parent_id TEXT,
                status TEXT DEFAULT 'testing',
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                win_rate REAL,
                total_pnl REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retired_at TIMESTAMP
            );
            
            -- Snapshots (periodic performance)
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                period_type TEXT NOT NULL,
                trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                win_rate REAL,
                total_pnl REAL DEFAULT 0,
                avg_pnl REAL,
                take_profits INTEGER DEFAULT 0,
                resolution_exits INTEGER DEFAULT 0,
                time_stops INTEGER DEFAULT 0,
                max_drawdown REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_snapshots_strategy ON snapshots(strategy_id);
            CREATE INDEX IF NOT EXISTS idx_snapshots_period ON snapshots(period_start, period_end);
            
            -- Insights (LLM generated)
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL,
                tested INTEGER DEFAULT 0,
                validated INTEGER DEFAULT 0,
                test_result TEXT,
                llm_model TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self._conn.commit()
    
    # ==================== Price Operations ====================
    
    async def save_price(self, price: PriceUpdate) -> None:
        """Save a price update."""
        await self._conn.execute("""
            INSERT INTO prices (
                market_id, condition_id, asset, yes_price, no_price,
                time_remaining, volume, liquidity, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            price.market_id, price.condition_id, price.asset,
            price.yes_price, price.no_price, price.time_remaining,
            price.volume, price.liquidity, price.timestamp.isoformat()
        ))
        await self._conn.commit()
    
    async def get_recent_prices(
        self, 
        market_id: str, 
        minutes: int = 5
    ) -> List[PriceUpdate]:
        """Get recent prices for a market."""
        cursor = await self._conn.execute("""
            SELECT * FROM prices
            WHERE market_id = ?
            AND timestamp > datetime('now', ?)
            ORDER BY timestamp DESC
        """, (market_id, f'-{minutes} minutes'))
        
        rows = await cursor.fetchall()
        return [PriceUpdate(
            market_id=row['market_id'],
            condition_id=row['condition_id'],
            asset=row['asset'],
            yes_price=row['yes_price'],
            no_price=row['no_price'],
            time_remaining=row['time_remaining'],
            volume=row['volume'],
            liquidity=row['liquidity'],
            timestamp=datetime.fromisoformat(row['timestamp'])
        ) for row in rows]
    
    # ==================== Trade Operations ====================
    
    async def save_trade(self, trade: Trade) -> int:
        """Save a trade and return its ID."""
        cursor = await self._conn.execute("""
            INSERT INTO trades (
                strategy_id, market_id, condition_id, asset, side,
                entry_price, exit_price, entry_time, exit_time, shares,
                pnl, pnl_pct, is_win, exit_reason,
                time_remaining_at_entry, time_remaining_at_exit,
                price_1min_ago, price_5min_ago, hour_of_day, day_of_week,
                market_volatility, status, is_paper
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.strategy_id, trade.market_id, trade.condition_id,
            trade.asset, trade.side.value, trade.entry_price, trade.exit_price,
            trade.entry_time.isoformat(),
            trade.exit_time.isoformat() if trade.exit_time else None,
            trade.shares, trade.pnl, trade.pnl_pct,
            1 if trade.is_win else (0 if trade.is_win is not None else None),
            trade.exit_reason.value if trade.exit_reason else None,
            trade.time_remaining_at_entry, trade.time_remaining_at_exit,
            trade.price_1min_ago, trade.price_5min_ago,
            trade.hour_of_day, trade.day_of_week,
            trade.market_volatility, trade.status.value, 1 if trade.is_paper else 0
        ))
        await self._conn.commit()
        return cursor.lastrowid
    
    async def update_trade(self, trade: Trade) -> None:
        """Update an existing trade."""
        await self._conn.execute("""
            UPDATE trades SET
                exit_price = ?,
                exit_time = ?,
                pnl = ?,
                pnl_pct = ?,
                is_win = ?,
                exit_reason = ?,
                time_remaining_at_exit = ?,
                status = ?
            WHERE id = ?
        """, (
            trade.exit_price,
            trade.exit_time.isoformat() if trade.exit_time else None,
            trade.pnl, trade.pnl_pct,
            1 if trade.is_win else (0 if trade.is_win is not None else None),
            trade.exit_reason.value if trade.exit_reason else None,
            trade.time_remaining_at_exit,
            trade.status.value,
            trade.id
        ))
        await self._conn.commit()
    
    async def get_open_trades(self, strategy_id: Optional[str] = None) -> List[Trade]:
        """Get all open trades, optionally filtered by strategy."""
        if strategy_id:
            cursor = await self._conn.execute(
                "SELECT * FROM trades WHERE status = 'open' AND strategy_id = ?",
                (strategy_id,)
            )
        else:
            cursor = await self._conn.execute(
                "SELECT * FROM trades WHERE status = 'open'"
            )
        
        rows = await cursor.fetchall()
        return [self._row_to_trade(row) for row in rows]
    
    async def get_trades_by_strategy(
        self, 
        strategy_id: str,
        limit: int = 100
    ) -> List[Trade]:
        """Get recent trades for a strategy."""
        cursor = await self._conn.execute("""
            SELECT * FROM trades
            WHERE strategy_id = ?
            ORDER BY entry_time DESC
            LIMIT ?
        """, (strategy_id, limit))
        
        rows = await cursor.fetchall()
        return [self._row_to_trade(row) for row in rows]
    
    def _row_to_trade(self, row) -> Trade:
        """Convert a database row to a Trade object."""
        return Trade(
            id=row['id'],
            strategy_id=row['strategy_id'],
            market_id=row['market_id'],
            condition_id=row['condition_id'],
            asset=row['asset'],
            side=Side(row['side']),
            entry_price=row['entry_price'],
            exit_price=row['exit_price'],
            entry_time=datetime.fromisoformat(row['entry_time']),
            exit_time=datetime.fromisoformat(row['exit_time']) if row['exit_time'] else None,
            shares=row['shares'],
            pnl=row['pnl'],
            pnl_pct=row['pnl_pct'],
            is_win=bool(row['is_win']) if row['is_win'] is not None else None,
            exit_reason=ExitReason(row['exit_reason']) if row['exit_reason'] else None,
            time_remaining_at_entry=row['time_remaining_at_entry'],
            time_remaining_at_exit=row['time_remaining_at_exit'],
            price_1min_ago=row['price_1min_ago'],
            price_5min_ago=row['price_5min_ago'],
            hour_of_day=row['hour_of_day'],
            day_of_week=row['day_of_week'],
            market_volatility=row['market_volatility'],
            status=TradeStatus(row['status']),
            is_paper=bool(row['is_paper'])
        )
    
    # ==================== Strategy Operations ====================
    
    async def save_strategy(self, strategy: Strategy) -> None:
        """Save or update a strategy."""
        await self._conn.execute("""
            INSERT OR REPLACE INTO strategies (
                id, name, tier, entry_threshold, exit_threshold, direction,
                generation, parent_id, status, total_trades, wins, losses,
                win_rate, total_pnl, created_at, retired_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy.id, strategy.name, strategy.tier,
            strategy.entry_threshold, strategy.exit_threshold, strategy.direction,
            strategy.generation, strategy.parent_id, strategy.status.value,
            strategy.total_trades, strategy.wins, strategy.losses,
            strategy.win_rate, strategy.total_pnl,
            strategy.created_at.isoformat(),
            strategy.retired_at.isoformat() if strategy.retired_at else None
        ))
        await self._conn.commit()
    
    async def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM strategies WHERE id = ?",
            (strategy_id,)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_strategy(row)
        return None
    
    async def get_active_strategies(self) -> List[Strategy]:
        """Get all active (non-retired) strategies."""
        cursor = await self._conn.execute(
            "SELECT * FROM strategies WHERE status != 'retired'"
        )
        rows = await cursor.fetchall()
        return [self._row_to_strategy(row) for row in rows]
    
    async def update_strategy_stats(self, strategy_id: str) -> None:
        """Recalculate and update strategy statistics."""
        cursor = await self._conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN is_win = 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl
            FROM trades
            WHERE strategy_id = ? AND status = 'closed'
        """, (strategy_id,))
        
        row = await cursor.fetchone()
        total = row['total'] or 0
        wins = row['wins'] or 0
        losses = row['losses'] or 0
        total_pnl = row['total_pnl'] or 0
        win_rate = wins / total if total > 0 else None
        
        await self._conn.execute("""
            UPDATE strategies SET
                total_trades = ?,
                wins = ?,
                losses = ?,
                win_rate = ?,
                total_pnl = ?
            WHERE id = ?
        """, (total, wins, losses, win_rate, total_pnl, strategy_id))
        await self._conn.commit()
    
    def _row_to_strategy(self, row) -> Strategy:
        """Convert a database row to a Strategy object."""
        return Strategy(
            id=row['id'],
            name=row['name'],
            tier=row['tier'],
            entry_threshold=row['entry_threshold'],
            exit_threshold=row['exit_threshold'],
            direction=row['direction'],
            generation=row['generation'],
            parent_id=row['parent_id'],
            status=StrategyStatus(row['status']),
            total_trades=row['total_trades'],
            wins=row['wins'],
            losses=row['losses'],
            win_rate=row['win_rate'],
            total_pnl=row['total_pnl'],
            created_at=datetime.fromisoformat(row['created_at']),
            retired_at=datetime.fromisoformat(row['retired_at']) if row['retired_at'] else None
        )
    
    # ==================== Analytics Queries ====================
    
    async def get_strategy_performance(self) -> List[dict]:
        """Get performance summary for all strategies."""
        cursor = await self._conn.execute("""
            SELECT 
                s.id,
                s.name,
                s.tier,
                s.entry_threshold,
                s.exit_threshold,
                s.status,
                COUNT(t.id) as total_trades,
                SUM(CASE WHEN t.is_win = 1 THEN 1 ELSE 0 END) as wins,
                ROUND(AVG(CASE WHEN t.is_win = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) as win_rate,
                ROUND(SUM(t.pnl), 2) as total_pnl,
                ROUND(AVG(t.pnl), 2) as avg_pnl
            FROM strategies s
            LEFT JOIN trades t ON s.id = t.strategy_id AND t.status = 'closed'
            WHERE s.status != 'retired'
            GROUP BY s.id
            ORDER BY win_rate DESC NULLS LAST
        """)
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# Global database instance
_db: Optional[Database] = None


async def get_database(db_path: str = "data/evolution.db") -> Database:
    """Get the global database instance."""
    global _db
    if _db is None:
        _db = Database(db_path)
        await _db.connect()
    return _db
