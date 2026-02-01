import sqlite3
import sys
from datetime import datetime

DB_PATH = "data/evolution.db"

def analyze():
    print("=" * 80)
    print(f"📊 STRATEGY PERFORMANCE AUDIT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Strategy Leaderboard
    print("\n🏆 STRATEGY LEADERBOARD (Sorted by P&L)")
    print("-" * 80)
    print(f"{'Strategy ID':<20} | {'Trades':<8} | {'Win Rate':<10} | {'Total P&L':<12} | {'Avg P&L':<10}")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            strategy_id,
            COUNT(*) as trades,
            SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
            SUM(pnl) as total_pnl,
            AVG(pnl) as avg_pnl
        FROM trades 
        WHERE status = 'closed'
        GROUP BY strategy_id
        ORDER BY total_pnl DESC
    """)
    
    for row in cursor.fetchall():
        trades = row['trades']
        wins = row['wins']
        win_rate = (wins / trades * 100) if trades > 0 else 0
        pnl = row['total_pnl'] or 0.0
        avg = row['avg_pnl'] or 0.0
        
        color = "🟢" if pnl > 0 else "🔴"
        print(f"{color} {row['strategy_id']:<17} | {trades:<8} | {win_rate:>6.1f}%   | ${pnl:>10.2f} | ${avg:>8.2f}")

    # 2. Open Positions
    print("\n📈 ACTIVE POSITIONS")
    print("-" * 80)
    print(f"{'Strategy':<15} | {'Asset':<5} | {'Side':<4} | {'Entry':<8} | {'Current (Est)':<14} | {'Time Open':<15}")
    print("-" * 80)
    
    cursor.execute("""
        SELECT * FROM trades 
        WHERE status = 'open' 
        ORDER BY entry_time DESC
    """)
    
    open_trades = cursor.fetchall()
    if not open_trades:
        print("   No open positions.")
    
    for row in open_trades:
        # Calculate time open
        entry_time = datetime.fromisoformat(row['entry_time'])
        duration = datetime.now() - entry_time
        print(f"{row['strategy_id']:<15} | {row['asset']:<5} | {row['side']:<4} | {row['entry_price']:<8.3f} | {'--':<14} | {str(duration).split('.')[0]}")

    # 3. Detailed Execution Log (Last 20)
    print("\n📜 RECENT EXECUTION LOG (Last 20 Actions)")
    print("-" * 80)
    print(f"{'Time':<20} | {'Action':<8} | {'Strategy':<15} | {'Asset':<5} | {'Price':<8} | {'Reason'}")
    print("-" * 80)
    
    cursor.execute("""
        SELECT * FROM trades 
        ORDER BY entry_time DESC 
        LIMIT 20
    """)
    
    for row in cursor.fetchall():
        # Entry
        print(f"{row['entry_time'][:19]:<20} | {'ENTRY':<8} | {row['strategy_id']:<15} | {row['asset']:<5} | {row['entry_price']:<8.3f} | Signal Triggered")
        
        # Exit (if closed)
        if row['status'] == 'closed':
            print(f"{row['exit_time'][:19]:<20} | {'EXIT':<8} | {row['strategy_id']:<15} | {row['asset']:<5} | {row['exit_price']:<8.3f} | {row['exit_reason']}")

    print("=" * 80)
    conn.close()

if __name__ == "__main__":
    analyze()
