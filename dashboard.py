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
    <title>PolyVol | Neural Trading Hub</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #05050a;
            --card-bg: rgba(15, 15, 25, 0.7);
            --accent: #00d4ff;
            --accent-glow: rgba(0, 212, 255, 0.4);
            --purple: #7b2ff7;
            --purple-glow: rgba(123, 47, 247, 0.4);
            --green: #00ff88;
            --red: #ff4444;
            --text: #e0e0e0;
            --text-dim: #888;
            --glass-border: rgba(255, 255, 255, 0.08);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Outfit', system-ui, sans-serif;
            background: var(--bg);
            background-image: 
                radial-gradient(circle at 0% 0%, var(--purple-glow) 0%, transparent 40%),
                radial-gradient(circle at 100% 100%, var(--accent-glow) 0%, transparent 40%);
            color: var(--text);
            min-height: 100vh;
            padding: 40px;
            line-height: 1.6;
        }

        .container { max-width: 1400px; margin: 0 auto; }
        
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 50px;
        }

        .logo {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -1px;
            background: linear-gradient(90deg, var(--accent), var(--purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--accent), var(--purple));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 20px var(--accent-glow);
        }

        .status-badge {
            background: rgba(0, 255, 136, 0.1);
            color: var(--green);
            padding: 8px 20px;
            border-radius: 50px;
            border: 1px solid rgba(0, 255, 136, 0.2);
            font-weight: 600;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
            100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
        }

        .grid-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            margin-bottom: 40px;
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 30px;
            position: relative;
            overflow: hidden;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .card:hover {
            transform: translateY(-8px);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .card h2 {
            font-size: 0.9rem;
            color: var(--text-dim);
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-weight: 600;
        }

        .stat-value {
            font-size: 3rem;
            font-weight: 700;
            letter-spacing: -1px;
            font-variant-numeric: tabular-nums;
        }

        .main-layout {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }

        .section-title {
            font-size: 1.5rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        /* Market Cards */
        .price-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }

        .market-card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 20px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .market-info {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .asset-name { font-size: 1.5rem; font-weight: 700; }
        .market-timer { font-family: 'JetBrains Mono'; color: var(--accent); }

        .price-bars {
            display: flex;
            gap: 10px;
            height: 40px;
        }

        .price-bar {
            flex: 1;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
            position: relative;
            overflow: hidden;
        }

        .price-bar.up { background: rgba(0, 255, 136, 0.15); color: var(--green); border: 1px solid rgba(0, 255, 136, 0.3); }
        .price-bar.down { background: rgba(255, 68, 68, 0.15); color: var(--red); border: 1px solid rgba(255, 68, 68, 0.3); }

        .signal-alert {
            background: linear-gradient(90deg, var(--accent), var(--purple));
            color: white;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 700;
            text-align: center;
            margin-top: 10px;
            animation: glow 1.5s infinite alternate;
        }

        @keyframes glow {
            from { box-shadow: 0 0 5px var(--accent); }
            to { box-shadow: 0 0 15px var(--purple); }
        }

        /* AI Insights Section */
        .insights-list {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .insight-item {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 20px;
            border-left: 4px solid var(--accent);
            transition: background 0.2s;
        }

        .insight-item:hover { background: rgba(255, 255, 255, 0.06); }

        .insight-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: var(--text-dim);
            margin-bottom: 8px;
        }

        .insight-title { font-weight: 600; margin-bottom: 8px; color: var(--accent); }
        .insight-desc { font-size: 0.95rem; color: #ccc; }

        /* Tables */
        .table-container {
            width: 100%;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 8px;
        }

        th {
            text-align: left;
            padding: 12px 20px;
            color: var(--text-dim);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 1px;
        }

        td {
            padding: 16px 20px;
            background: rgba(255, 255, 255, 0.02);
            font-size: 0.95rem;
        }

        td:first-child { border-radius: 12px 0 0 12px; }
        td:last-child { border-radius: 0 12px 12px 0; }

        .badge {
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        .badge.win { background: rgba(0, 255, 136, 0.1); color: var(--green); border: 1px solid rgba(0, 255, 136, 0.2); }
        .badge.loss { background: rgba(255, 68, 68, 0.1); color: var(--red); border: 1px solid rgba(255, 68, 68, 0.2); }
        .badge.open { background: rgba(0, 212, 255, 0.1); color: var(--accent); border: 1px solid rgba(0, 212, 255, 0.2); }

        .footer {
            margin-top: 50px;
            text-align: center;
            color: var(--text-dim);
            font-size: 0.9rem;
            padding: 20px;
            border-top: 1px solid var(--glass-border);
        }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">⚡</div>
                POLYVOL <span style="font-weight: 300; opacity: 0.5;">HUB</span>
            </div>
            <div class="status-badge">
                <div style="width: 8px; height: 8px; border-radius: 50%; background: var(--green);"></div>
                NEURAL ENGINE ACTIVE
            </div>
        </header>
        
        <div class="grid-stats">
            <div class="card">
                <h2>Total Volume</h2>
                <div class="stat-value" id="total-trades" style="color: var(--accent);">--</div>
            </div>
            <div class="card">
                <h2>Win Accuracy</h2>
                <div class="stat-value" id="win-rate">--%</div>
            </div>
            <div class="card">
                <h2>Total P&L</h2>
                <div class="stat-value" id="total-pnl">--</div>
            </div>
            <div class="card">
                <h2>Live Threads</h2>
                <div class="stat-value" id="open-positions" style="color: var(--purple);">--</div>
            </div>
        </div>
        
        <div class="main-layout">
            <div class="left-col">
                <div class="card" style="margin-bottom: 24px;">
                    <div class="section-header">
                        <div class="section-title">💹 Market Liquidity</div>
                    </div>
                    <div class="price-grid" id="prices">
                        <!-- Prices go here -->
                    </div>
                </div>

                <div class="card">
                    <div class="section-header">
                        <div class="section-title">🎯 Neural Strategies</div>
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Range</th>
                                    <th>Volume</th>
                                    <th>Accuracy</th>
                                    <th>Alpha</th>
                                </tr>
                            </thead>
                            <tbody id="strategies">
                                <!-- Strategies go here -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="right-col">
                <div class="card" style="margin-bottom: 24px; min-height: 400px;">
                    <div class="section-header">
                        <div class="section-title">🧠 AI Friend Insights</div>
                    </div>
                    <div class="insights-list" id="insights">
                        <div class="insight-item" style="border-left-color: #888; color: #888;">
                            Waiting for next neural cycle...
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="section-header">
                        <div class="section-title">📜 Execution Log</div>
                    </div>
                    <div id="trades" style="display: flex; flex-direction: column; gap: 12px;">
                        <!-- Trades go here -->
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Neural Trading Bot v3.0 | <span id="last-update">Syncing...</span>
        </div>
    </div>
    
    <script>
        async function fetchData() {
            try {
                const [basicResp, insightsResp] = await Promise.all([
                    fetch('/api/data?t=' + Date.now()),
                    fetch('/api/insights?t=' + Date.now())
                ]);
                
                const data = await basicResp.json();
                const insightsData = await insightsResp.json();
                
                // Stats
                document.getElementById('total-trades').textContent = data.total_trades;
                document.getElementById('win-rate').textContent = data.win_rate + '%';
                document.getElementById('win-rate').style.color = data.win_rate >= 60 ? 'var(--green)' : (data.win_rate >= 50 ? 'var(--accent)' : 'var(--red)');
                document.getElementById('total-pnl').textContent = (data.total_pnl >= 0 ? '+' : '') + '$' + data.total_pnl.toFixed(2);
                document.getElementById('total-pnl').style.color = data.total_pnl >= 0 ? 'var(--green)' : 'var(--red)';
                document.getElementById('open-positions').textContent = data.open_positions;
                
                // Prices
                let pricesHtml = '';
                for (const p of data.prices) {
                    const yesPct = (p.yes * 100).toFixed(1);
                    const noPct = (p.no * 100).toFixed(1);
                    pricesHtml += `
                        <div class="market-card">
                            <div class="market-info">
                                <div class="asset-name">${p.asset}</div>
                                <div class="market-timer">15m Market</div>
                            </div>
                            <div class="price-bars">
                                <div class="price-bar up" style="flex: ${p.yes};">UP ${yesPct}%</div>
                                <div class="price-bar down" style="flex: ${p.no};">DN ${noPct}%</div>
                            </div>
                            ${p.signal ? `<div class="signal-alert">${p.signal}</div>` : ''}
                        </div>
                    `;
                }
                document.getElementById('prices').innerHTML = pricesHtml || '<div class="market-card">No active markets</div>';
                
                // Strategies
                let stratHtml = '';
                for (const s of data.strategies) {
                    stratHtml += `
                        <tr>
                            <td style="font-weight: 600;">${s.id}</td>
                            <td style="font-family: 'JetBrains Mono';">${(s.entry * 100).toFixed(0)}% → ${(s.exit * 100).toFixed(0)}%</td>
                            <td>${s.trades}</td>
                            <td>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <div style="width: 60px; height: 6px; background: rgba(255,255,255,0.1); border-radius: 10px;">
                                        <div style="width: ${s.win_rate}%; height: 100%; height:100%; background: ${s.win_rate >= 60 ? 'var(--green)' : 'var(--accent)'}; border-radius: 10px;"></div>
                                    </div>
                                    ${s.win_rate.toFixed(1)}%
                                </div>
                            </td>
                            <td style="color: ${s.pnl >= 0 ? 'var(--green)' : 'var(--red)'}; font-weight: 600;">
                                ${s.pnl >= 0 ? '+' : ''}$${s.pnl.toFixed(2)}
                            </td>
                        </tr>
                    `;
                }
                document.getElementById('strategies').innerHTML = stratHtml || '<tr><td colspan="5">Initializing neural weights...</td></tr>';
                
                // Insights
                let insightsHtml = '';
                if (insightsData.insights && insightsData.insights.length > 0) {
                    for (const i of insightsData.insights.slice(0, 5)) {
                        const color = i.priority === 'high' ? 'var(--red)' : (i.priority === 'medium' ? 'var(--accent)' : 'var(--purple)');
                        insightsHtml += `
                            <div class="insight-item" style="border-left-color: ${color}">
                                <div class="insight-meta">
                                    <span>${i.category.toUpperCase()}</span>
                                    <span style="color: ${color}">${i.priority.toUpperCase()}</span>
                                </div>
                                <div class="insight-title">${i.title}</div>
                                <div class="insight-desc">${i.description}</div>
                                ${i.action ? `<div style="font-size: 0.8rem; margin-top: 10px; color: var(--accent); font-family: 'JetBrains Mono';">ACTION: ${i.action}</div>` : ''}
                            </div>
                        `;
                    }
                } else {
                    insightsHtml = `
                        <div class="insight-item" style="border-left-color: var(--text-dim); opacity: 0.5;">
                            <div class="insight-title">Neural Engine Idle</div>
                            <div class="insight-desc">Connect OpenRouter API key to activate AI Friend insights and strategy evolution.</div>
                        </div>
                    `;
                }
                document.getElementById('insights').innerHTML = insightsHtml;

                // Trades
                let tradesHtml = '';
                for (const t of data.recent_trades.slice(0, 10)) {
                    const statusClass = t.is_win ? 'win' : (t.status === 'open' ? 'open' : 'loss');
                    const statusText = t.status === 'open' ? 'Live' : (t.is_win ? 'Win' : 'Loss');
                    tradesHtml += `
                        <div style="background: rgba(255,255,255,0.02); padding: 12px 20px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 0.75rem; color: var(--text-dim);">${t.time.split('T')[1]?.slice(0,8) || t.time}</div>
                                <div style="font-weight: 600;">${t.asset} <span style="font-weight: 300;">${t.side}</span></div>
                            </div>
                            <div style="text-align: right;">
                                <div class="badge ${statusClass}">${statusText}</div>
                                <div style="font-size: 0.8rem; margin-top: 4px; color: ${t.is_win ? 'var(--green)' : (t.status === 'open' ? 'var(--accent)' : 'var(--red)')}">
                                    $${t.wager.toFixed(2)} @ ${(t.entry * 100).toFixed(0)}%
                                </div>
                            </div>
                        </div>
                    `;
                }
                document.getElementById('trades').innerHTML = tradesHtml || '<div style="opacity: 0.5; text-align: center; padding: 20px;">Watching for market anomalies...</div>';
                
                document.getElementById('last-update').textContent = 'Last Sync: ' + new Date().toLocaleTimeString();
                
            } catch (e) {
                console.error('Core sync error:', e);
            }
        }
        
        setInterval(fetchData, 2000);
        fetchData();
    </script>
</body>
</html>
"""
""


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


@app.route('/api/insights')
def api_insights():
    """Get AI-generated insights from the database."""
    import json
    
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get recent insights
    cursor.execute("""
        SELECT content, llm_model, created_at
        FROM insights
        ORDER BY created_at DESC
        LIMIT 20
    """)
    
    insights = []
    for row in cursor.fetchall():
        try:
            insight = json.loads(row['content'])
            insight['model'] = row['llm_model']
            insight['created_at'] = row['created_at']
            insights.append(insight)
        except json.JSONDecodeError:
            pass
    
    conn.close()
    
    return jsonify({
        'insights': insights,
        'count': len(insights)
    })


if __name__ == '__main__':
    print("=" * 60)
    print("POLYMARKET BOT DASHBOARD")
    print("=" * 60)
    print("Open http://localhost:5555 in your browser")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5555, debug=False)
