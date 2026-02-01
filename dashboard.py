"""
Simple Web Dashboard for Polymarket Volatility Bot.
Run alongside the main bot to monitor performance.
"""
import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template_string, jsonify
import threading

app = Flask(__name__)
DB_PATH = "data/evolution.db"

# Dashboard HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Volatility Bot Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        
        h1 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 30px;
            background: linear-gradient(90deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .card h2 {
            font-size: 1.2rem;
            color: #888;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #fff;
        }
        .stat-value.green { color: #00ff88; }
        .stat-value.red { color: #ff4444; }
        .stat-value.blue { color: #00d4ff; }
        
        .price-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .price-item {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
        }
        .price-item h3 {
            font-size: 1.5rem;
            margin-bottom: 10px;
        }
        .price-item .up { color: #00ff88; }
        .price-item .down { color: #ff4444; }
        .price-item .label { color: #888; font-size: 0.8rem; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        th { color: #888; font-weight: normal; text-transform: uppercase; font-size: 0.8rem; }
        
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        .badge.win { background: rgba(0, 255, 136, 0.2); color: #00ff88; }
        .badge.loss { background: rgba(255, 68, 68, 0.2); color: #ff4444; }
        .badge.open { background: rgba(0, 212, 255, 0.2); color: #00d4ff; }
        
        .refresh-note {
            text-align: center;
            color: #666;
            margin-top: 20px;
            font-size: 0.9rem;
        }
        
        .strategy-row { transition: background 0.2s; }
        .strategy-row:hover { background: rgba(255, 255, 255, 0.05); }
        
        .progress-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }
        .progress-bar .fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s;
        }
        .progress-bar .fill.good { background: linear-gradient(90deg, #00ff88, #00d4ff); }
        .progress-bar .fill.bad { background: linear-gradient(90deg, #ff4444, #ff8800); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Polymarket Volatility Bot</h1>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Total Trades</h2>
                <div class="stat-value blue" id="total-trades">--</div>
            </div>
            <div class="card">
                <h2>✅ Win Rate</h2>
                <div class="stat-value green" id="win-rate">--%</div>
            </div>
            <div class="card">
                <h2>💰 Total P&L</h2>
                <div class="stat-value" id="total-pnl">$--</div>
            </div>
            <div class="card">
                <h2>📈 Open Positions</h2>
                <div class="stat-value blue" id="open-positions">--</div>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 30px;">
            <h2>💹 Live Market Prices</h2>
            <div class="price-grid" id="prices">
                <div class="price-item">
                    <h3>Loading...</h3>
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 30px;">
            <h2>🎯 Strategy Performance</h2>
            <table>
                <thead>
                    <tr>
                        <th>Strategy</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody id="strategies">
                    <tr><td colspan="6">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>📜 Recent Trades</h2>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Strategy</th>
                        <th>Asset</th>
                        <th>Side</th>
                        <th>Wager</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Result</th>
                    </tr>
                </thead>
                <tbody id="trades">
                    <tr><td colspan="7">No trades yet...</td></tr>
                </tbody>
            </table>
        </div>
        
        <p class="refresh-note">Auto-refreshes every 5 seconds | Bot running since startup</p>
    </div>
    
    <script>
        async function fetchData() {
            try {
                const resp = await fetch('/api/data?t=' + new Date().getTime());
                const data = await resp.json();
                
                // Update stats
                document.getElementById('total-trades').textContent = data.total_trades;
                document.getElementById('win-rate').textContent = data.win_rate + '%';
                document.getElementById('win-rate').className = 'stat-value ' + (parseFloat(data.win_rate) >= 50 ? 'green' : 'red');
                document.getElementById('total-pnl').textContent = '$' + data.total_pnl.toFixed(2);
                document.getElementById('total-pnl').className = 'stat-value ' + (data.total_pnl >= 0 ? 'green' : 'red');
                document.getElementById('open-positions').textContent = data.open_positions;
                
                // Update prices
                let pricesHtml = '';
                for (const p of data.prices) {
                    pricesHtml += `
                        <div class="price-item">
                            <h3>${p.asset}</h3>
                            <div class="up">${(p.yes * 100).toFixed(1)}% Up</div>
                            <div class="down">${(p.no * 100).toFixed(1)}% Down</div>
                            <div class="label">${p.signal || 'Waiting...'}</div>
                        </div>
                    `;
                }
                document.getElementById('prices').innerHTML = pricesHtml || '<div class="price-item"><h3>No markets</h3></div>';
                
                // Update strategies
                let stratHtml = '';
                for (const s of data.strategies) {
                    const wrClass = s.win_rate >= 60 ? 'good' : 'bad';
                    stratHtml += `
                        <tr class="strategy-row">
                            <td><strong>${s.id}</strong></td>
                            <td>${(s.entry * 100).toFixed(0)}%</td>
                            <td>${(s.exit * 100).toFixed(0)}%</td>
                            <td>${s.trades}</td>
                            <td>
                                ${s.win_rate.toFixed(1)}%
                                <div class="progress-bar">
                                    <div class="fill ${wrClass}" style="width: ${s.win_rate}%"></div>
                                </div>
                            </td>
                            <td style="color: ${s.pnl >= 0 ? '#00ff88' : '#ff4444'}">
                                ${s.pnl >= 0 ? '+' : ''}$${s.pnl.toFixed(2)}
                            </td>
                        </tr>
                    `;
                }
                document.getElementById('strategies').innerHTML = stratHtml || '<tr><td colspan="6">No strategy data yet</td></tr>';
                
                // Update trades
                let tradesHtml = '';
                for (const t of data.recent_trades) {
                    const resultClass = t.is_win ? 'win' : (t.status === 'open' ? 'open' : 'loss');
                    const resultText = t.status === 'open' ? 'OPEN' : (t.is_win ? 'WIN' : 'LOSS');
                    tradesHtml += `
                        <tr>
                            <td>${t.time}</td>
                            <td>${t.strategy}</td>
                            <td>${t.asset}</td>
                            <td>${t.side}</td>
                            <td>$${t.wager.toFixed(2)}</td>
                            <td>${(t.entry * 100).toFixed(1)}%</td>
                            <td>${t.exit ? (t.exit * 100).toFixed(1) + '%' : '--'}</td>
                            <td><span class="badge ${resultClass}">${resultText}</span></td>
                        </tr>
                    `;
                }
                document.getElementById('trades').innerHTML = tradesHtml || '<tr><td colspan="7">No trades yet - waiting for opportunities...</td></tr>';
                
                // Update timestamp
                const now = new Date();
                document.querySelector('.refresh-note').innerHTML = `Auto-refreshes every 1s | Last updated: ${now.toLocaleTimeString()}`;
                
            } catch (e) {
                console.error('Error fetching data:', e);
                document.querySelector('.refresh-note').innerHTML = `<span style="color:red">Connection lost... retrying</span>`;
            }
        }
        
        // Initial fetch and refresh every 5 seconds
        fetchData();
        setInterval(fetchData, 3000);  // Update every 3 seconds
    </script>
</body>
</html>
"""


def get_db():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


@app.route('/')
def dashboard():
    """Serve the dashboard."""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/data')
def api_data():
    """Get all dashboard data."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get trade stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN status = 'closed' THEN COALESCE(pnl_pct, 0) * shares * entry_price ELSE 0 END) as total_pnl,
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_count
        FROM trades
    """)
    stats = cursor.fetchone()
    
    total_trades = stats['total'] or 0
    wins = stats['wins'] or 0
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    total_pnl = stats['total_pnl'] or 0
    open_positions = stats['open_count'] or 0
    
    # Get recent prices
    cursor.execute("""
        SELECT asset, yes_price, no_price, timestamp
        FROM prices
        WHERE timestamp > datetime('now', '-5 minute')
        ORDER BY id DESC
    """)
    raw_rows = cursor.fetchall()
    
    prices_map = {}
    for p in raw_rows:
        asset = p['asset']
        is_50 = abs(p['yes_price'] - 0.5) < 0.01
        
        if asset not in prices_map:
            prices_map[asset] = p
        else:
            curr_50 = abs(prices_map[asset]['yes_price'] - 0.5) < 0.01
            if curr_50 and not is_50:
                prices_map[asset] = p
    
    prices = []
    for asset in sorted(prices_map.keys()):
        p = prices_map[asset]
        signal = None
        if p['yes_price'] <= 0.20:
            signal = "🎯 BUY YES Signal!"
        elif p['no_price'] <= 0.20:
            signal = "🎯 BUY NO Signal!"
        
        prices.append({
            'asset': p['asset'],
            'yes': p['yes_price'],
            'no': p['no_price'],
            'signal': signal
        })
    
    # If no recent prices, show placeholder
    if not prices:
        prices = [
            {'asset': 'BTC', 'yes': 0.50, 'no': 0.50, 'signal': 'Connecting...'},
            {'asset': 'ETH', 'yes': 0.50, 'no': 0.50, 'signal': 'Connecting...'},
            {'asset': 'SOL', 'yes': 0.50, 'no': 0.50, 'signal': 'Connecting...'},
            {'asset': 'XRP', 'yes': 0.50, 'no': 0.50, 'signal': 'Connecting...'},
        ]
    
    # Get strategy performance
    cursor.execute("""
        SELECT 
            s.id,
            s.entry_threshold as entry,
            s.exit_threshold as exit,
            COUNT(t.id) as trades,
            COALESCE(AVG(CASE WHEN t.is_win = 1 THEN 100.0 ELSE 0.0 END), 0) as win_rate,
            COALESCE(SUM(t.pnl_pct * t.shares * t.entry_price), 0) as pnl
        FROM strategies s
        LEFT JOIN trades t ON s.id = t.strategy_id AND t.status = 'closed'
        GROUP BY s.id
        ORDER BY s.entry_threshold
    """)
    strategies = [dict(row) for row in cursor.fetchall()]
    
    # Get recent trades
    cursor.execute("""
        SELECT 
            strategy_id as strategy,
            asset,
            side,
            shares,
            entry_price as entry,
            exit_price as exit,
            is_win,
            status,
            entry_time as time
        FROM trades
        ORDER BY entry_time DESC
        LIMIT 20
    """)
    trades = []
    for row in cursor.fetchall():
        trades.append({
            'strategy': row['strategy'],
            'asset': row['asset'],
            'side': row['side'],
            'wager': row['shares'] * row['entry'],
            'entry': row['entry'],
            'exit': row['exit'],
            'is_win': row['is_win'],
            'status': row['status'],
            'time': row['time'][:19] if row['time'] else ''
        })
    
    conn.close()
    
    return jsonify({
        'total_trades': total_trades,
        'win_rate': round(win_rate, 1),
        'total_pnl': total_pnl,
        'open_positions': open_positions,
        'prices': prices,
        'strategies': strategies,
        'recent_trades': trades
    })


if __name__ == '__main__':
    print("=" * 60)
    print("POLYMARKET BOT DASHBOARD")
    print("=" * 60)
    print("Open http://localhost:5555 in your browser")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5555, debug=False)
