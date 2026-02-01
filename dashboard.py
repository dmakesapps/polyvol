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
            padding: 8px 16px;
            border-radius: 50px;
            border: 1px solid rgba(0, 255, 136, 0.2);
            font-weight: 600;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .mode-toggle {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            color: var(--text);
            padding: 8px 16px;
            border-radius: 50px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .mode-toggle:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--accent);
        }

        .mode-toggle.live {
            color: var(--accent);
            border-color: var(--accent);
            background: rgba(0, 212, 255, 0.1);
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

        /* AI Action Log */
        .action-log {
            max-height: 200px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .action-log-item {
            padding: 10px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 10px;
            font-size: 0.85rem;
            border-left: 3px solid var(--accent);
        }
        .action-log-meta { font-size: 0.75rem; color: var(--text-dim); display: flex; justify-content: space-between; margin-bottom: 4px; }
        .action-log-title { font-weight: 600; color: var(--accent); }

        /* AI Chat */
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 400px;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 15px;
        }
        .chat-bubble {
            max-width: 85%;
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 0.95rem;
            position: relative;
        }
        .chat-bubble.ai {
            align-self: flex-start;
            background: rgba(123, 47, 247, 0.15);
            border: 1px solid rgba(123, 47, 247, 0.3);
            border-bottom-left-radius: 4px;
        }
        .chat-bubble.user {
            align-self: flex-end;
            background: rgba(0, 212, 255, 0.15);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-bottom-right-radius: 4px;
        }
        .chat-input-area {
            display: flex;
            gap: 10px;
        }
        .chat-input {
            flex: 1;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            border-radius: 12px;
            padding: 12px 16px;
            color: white;
            outline: none;
            transition: border-color 0.2s;
        }
        .chat-input:focus { border-color: var(--accent); }
        .chat-send {
            background: linear-gradient(135deg, var(--accent), var(--purple));
            border: none;
            color: white;
            padding: 0 20px;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .chat-send:active { transform: scale(0.95); }

        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">PV</div>
                PolyVol Hub
            </div>
            <div style="display: flex; gap: 15px;">
                <button id="mode-btn" class="mode-toggle" onclick="toggleMode()">
                    <span id="mode-text">Loading Mode...</span>
                </button>
                <div class="status-badge">
                    <div style="width: 8px; height: 8px; background: var(--green); border-radius: 50%; animation: pulse 2s infinite;"></div>
                    NEURAL ENGINE ACTIVE
                </div>
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
        
        <div class="main-layout" style="margin-bottom: 24px;">
            <div class="left-col" style="grid-column: span 2;">
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
                <div class="card" style="height: 100%;">
                    <div class="section-header">
                        <div class="section-title">🧠 AI Friend Insights</div>
                    </div>
                    <div class="insights-list" id="insights" style="max-height: 600px; overflow-y: auto;">
                        <div class="insight-item" style="border-left-color: #888; color: #888;">
                            Waiting for next neural cycle...
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="main-layout" style="grid-template-columns: 1fr 1fr 1fr; margin-top: 24px;">
            <div class="card">
                <div class="section-header">
                    <div class="section-title">🤖 Neural Chat</div>
                </div>
                <div class="chat-container">
                    <div class="chat-messages" id="chat-messages">
                        <div class="chat-bubble ai">Welcome to the Neural Command Center. I am your AI Strategy Optimizer. How can I assist you today?</div>
                    </div>
                    <div class="chat-input-area">
                        <input type="text" id="chat-input" class="chat-input" placeholder="Give me a command...">
                        <button id="chat-send" class="chat-send">Send</button>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="section-header">
                    <div class="section-title">⚡ AI Action Log</div>
                </div>
                <div class="action-log" id="action-log">
                    <div style="color: var(--text-dim); text-align: center; padding-top: 50px;">Waiting for autonomous actions...</div>
                </div>
            </div>

            <div class="card" style="grid-column: span 3;">
                <div class="section-header">
                    <div class="section-title">📜 Extensive Execution Log</div>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 8px 15px; display: grid; grid-template-columns: 80px 100px 1fr 1fr 100px; font-size: 0.7rem; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px;">
                    <div>Time</div>
                    <div>Asset</div>
                    <div>Entry</div>
                    <div>Exit / PnL</div>
                    <div style="text-align: right;">Status</div>
                </div>
                <div id="trades" style="display: flex; flex-direction: column; max-height: 500px; overflow-y: auto;">
                    <!-- Trades go here -->
                </div>
            </div>
        </div>
        
        <div class="footer">
            Neural Trading Bot v3.0 | <span id="last-update">Syncing...</span>
        </div>
    </div>
    
    <script>
        function addMessage(role, message) {
            const container = document.getElementById('chat-messages');
            const bubble = document.createElement('div');
            bubble.className = `chat-bubble ${role.toLowerCase()}`;
            bubble.textContent = message;
            container.appendChild(bubble);
            container.scrollTop = container.scrollHeight;
        }

        async function toggleMode() {
            const btn = document.getElementById('mode-btn');
            btn.innerHTML = 'Switching...';
            try {
                const resp = await fetch('/api/toggle_mode', { method: 'POST' });
                const data = await resp.json();
                if (data.success) {
                    updateModeUI(data.new_mode);
                    addMessage('SYSTEM', `Trading mode switched to ${data.new_mode.toUpperCase()}. Please restart the bot to apply changes.`);
                }
            } catch (err) {
                console.error('Toggle failed:', err);
            }
        }

        async function fetchMode() {
            try {
                const resp = await fetch('/api/mode');
                const data = await resp.json();
                updateModeUI(data.mode);
            } catch (err) {}
        }

        function updateModeUI(mode) {
            const btn = document.getElementById('mode-btn');
            const text = document.getElementById('mode-text');
            text.textContent = mode.toUpperCase() + ' MODE';
            if (mode === 'live') {
                btn.className = 'mode-toggle live';
            } else {
                btn.className = 'mode-toggle';
            }
        }

        async function fetchData() {
            fetchMode();
            try {
                const [basicResp, insightsResp, actionsResp, chatResp] = await Promise.all([
                    fetch('/api/data?t=' + Date.now()),
                    fetch('/api/insights?t=' + Date.now()),
                    fetch('/api/actions?t=' + Date.now()),
                    fetch('/api/chat_history?t=' + Date.now())
                ]);
                
                const data = await basicResp.json();
                const insightsData = await insightsResp.json();
                const actionsData = await actionsResp.json();
                const chatData = await chatResp.json();
                
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
                    insightsHtml = `<div class="insight-item" style="border-left-color: #888; color: #888;">Waiting for next neural cycle...</div>`;
                }
                document.getElementById('insights').innerHTML = insightsHtml;

                // AI Action Log
                let actionsHtml = '';
                if (actionsData.actions && actionsData.actions.length > 0) {
                    for (const a of actionsData.actions) {
                        actionsHtml += `
                            <div class="action-log-item">
                                <div class="action-log-meta">
                                    <span>${a.time}</span>
                                    <span style="color: ${a.action === 'ENABLED' ? 'var(--green)' : 'var(--red)'}">${a.action}</span>
                                </div>
                                <div class="action-log-title">Strategy: ${a.strategy}</div>
                                <div style="font-size: 0.8rem; color: #ccc; margin-top: 4px;">Reason: ${a.reason}</div>
                            </div>
                        `;
                    }
                } else {
                    actionsHtml = '<div style="color: var(--text-dim); text-align: center; padding-top: 50px;">Waiting for autonomous actions...</div>';
                }
                document.getElementById('action-log').innerHTML = actionsHtml;

                // AI Chat
                let chatHtml = '';
                for (const msg of chatData.chat) {
                    chatHtml += `<div class="chat-bubble ${msg.role}">${msg.message}</div>`;
                }
                if (!chatHtml) {
                    chatHtml = '<div class="chat-bubble ai">Welcome to the Neural Command Center. I am your AI Strategy Optimizer. How can I assist you today?</div>';
                }
                if (document.getElementById('chat-messages').innerHTML !== chatHtml) {
                    document.getElementById('chat-messages').innerHTML = chatHtml;
                    document.getElementById('chat-messages').scrollTop = document.getElementById('chat-messages').scrollHeight;
                }

                // Extensive Execution Log
                let tradesHtml = '';
                for (const t of data.recent_trades.slice(0, 15)) {
                    // Surgical Badge Logic: A 'Win' MUST be profitable.
                    const isProfitable = (t.exit - t.entry) > 0;
                    const statusClass = t.status === 'open' ? 'open' : (isProfitable ? 'win' : 'loss');
                    const statusText = t.status === 'open' ? 'LIVE' : (isProfitable ? 'WIN' : 'LOSS');
                    const entryPriceLabel = (t.entry * 100).toFixed(0) + '%';
                    const exitPriceLabel = t.exit ? (t.exit * 100).toFixed(1) + '%' : '--';
                    
                    // Calculate PnL % for display
                    let pnlPercent = '';
                    if (t.status === 'closed' && t.exit) {
                        const change = (t.exit - t.entry) / t.entry * 100;
                        pnlPercent = `<span style="color: ${change >= 0 ? 'var(--green)' : 'var(--red)'}; margin-left:8px;">${change >= 0 ? '+' : ''}${change.toFixed(1)}%</span>`;
                    }

                    tradesHtml += `
                        <div style="background: rgba(255,255,255,0.02); border-bottom: 1px solid rgba(255,255,255,0.05); padding: 10px 15px; display: grid; grid-template-columns: 80px 100px 1fr 1fr 100px; align-items: center; font-size: 0.9rem;">
                            <div style="font-family: 'JetBrains Mono'; font-size: 0.7rem; color: var(--text-dim);">${t.time.split('T')[1]?.slice(0,5) || t.time}</div>
                            <div style="font-weight: 600; color: var(--accent);">${t.asset}</div>
                            <div>
                                <span style="font-size: 0.7rem; color: var(--text-dim);">IN:</span> 
                                <span style="font-family: 'JetBrains Mono';">${entryPriceLabel}</span>
                            </div>
                            <div>
                                <span style="font-size: 0.7rem; color: var(--text-dim);">OUT:</span> 
                                <span style="font-family: 'JetBrains Mono';">${exitPriceLabel}</span>
                                ${pnlPercent}
                            </div>
                            <div style="text-align: right;">
                                <span class="badge ${statusClass}" style="font-size: 0.65rem; padding: 2px 8px;">${statusText}</span>
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

        async function sendChat() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            
            input.value = '';
            input.disabled = true;
            
            try {
                const resp = await fetch('/api/ai_chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });
                await fetchData();
            } catch (e) {
                console.error('Chat error:', e);
            } finally {
                input.disabled = false;
                input.focus();
            }
        }

        document.getElementById('chat-send').onclick = sendChat;
        document.getElementById('chat-input').onkeypress = (e) => { if (e.key === 'Enter') sendChat(); };
        
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
    
@app.route('/api/actions')
def api_actions():
    """Get history of AI auto-applied actions."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT action, strategy_id, reason, created_at
        FROM ai_actions
        ORDER BY created_at DESC
        LIMIT 50
    """)
    
    actions = []
    for row in cursor.fetchall():
        actions.append({
            'action': row['action'],
            'strategy': row['strategy_id'],
            'reason': row['reason'],
            'time': row['created_at'][:19]
        })
    
    conn.close()
    return jsonify({'actions': actions})


@app.route('/api/chat_history')
def api_chat_history():
    """Get the conversation history."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT role, message FROM ai_chat ORDER BY id ASC LIMIT 100")
    chat = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify({'chat': chat})


@app.route('/api/ai_chat', methods=['POST'])
def api_ai_chat():
    """Handle chat with the AI Friend."""
    from flask import request
    import httpx
    import os
    from dotenv import load_dotenv
    import json

    load_dotenv('config/.env')
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        return jsonify({'error': 'No API key'}), 401
        
    data = request.json
    user_msg = data.get('message', '')
    
    if not user_msg:
        return jsonify({'error': 'Empty message'}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Save user message
    cursor.execute("INSERT INTO ai_chat (role, message) VALUES (?, ?)", ('user', user_msg))
    conn.commit()
    
    # 2. Get history for context
    cursor.execute("SELECT role, message FROM ai_chat ORDER BY id DESC LIMIT 10")
    history = cursor.fetchall()[::-1]
    messages = [{"role": m[0], "content": m[1]} for m in history]
    
    # 2.5 Get recent trade data for the Surgeon to analyze
    cursor.execute("""
        SELECT asset, side, entry_price, exit_price, pnl_pct, exit_reason, entry_time 
        FROM trades 
        WHERE status = 'closed' 
        ORDER BY created_at DESC LIMIT 10
    """)
    recent_trades = cursor.fetchall()
    trade_summary = "\n".join([
        f"- {t[6]}: {t[0]} {t[1]} | Entry: {t[2]:.2f} | Exit: {t[3]:.2f} | PnL: {t[4]*100:.1f}% | Reason: {t[5]}"
        for t in recent_trades
    ])

    # Updated System Prompt for "The Algorithmic Surgeon"
    system_prompt = {
        "role": "system",
        "content": f"""You are THE ALGORITHMIC SURGEON, a high-frequency strategy optimizer for 15-minute Polymarket crypto markets. 
        Your objective is simple: PRODUCE PROFITS and STOP THE BLEEDING.
        
        CRITICAL OPERATING PROCEDURES:
        1. DATA-FIRST REASONING: Analyze the provided trade logs. Identify 'Resolution Exits' (deaths) vs 'Take Profits' (wins).
        2. PYTHON-POWERED: You can suggest specific changes to the Python code in src/strategies/ or src/analysis/.
        3. DEEP THINKING: Take your time. Don't give a fast answer. 
        4. SURGICAL MODIFICATION: Recommend disabling specific Tier IDs if their win rate is low.
        
        RECENT TRADE LOGS FOR ANALYSIS:
        {trade_summary if trade_summary else "No closed trades yet."}
        
        Identity: You are slightly futuristic, professional, and obsessed with math and ROI.
        Current Context: Analyze the provided logs to explain recent performance."""
    }
    messages.insert(0, system_prompt)
    
    # 3. Call OpenRouter with Think Mode (Gemini 2.0 Flash Thinking)
    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://polyvol.dashboard",
                "X-Title": "PolyVol Hub"
            },
            json={
                "model": "google/gemini-2.0-flash-thinking-exp-1219",
                "messages": messages,
                "include_reasoning": True
            },
            timeout=120.0 # High timeout for deep thinking
        )
        
        if response.status_code == 200:
            ai_msg = response.json()['choices'][0]['message']['content']
            cursor.execute("INSERT INTO ai_chat (role, message) VALUES (?, ?)", ('ai', ai_msg))
            conn.commit()
            return jsonify({'response': ai_msg})
        else:
            return jsonify({'error': f"AI Error: {response.text}"}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/mode', methods=['GET'])
def get_mode():
    """Get the current trading mode from .env."""
    env_path = Path("config/.env")
    if not env_path.exists():
        return jsonify({"mode": "unknown"})
    
    with open(env_path, "r") as f:
        content = f.read()
        for line in content.splitlines():
            if line.startswith("MODE="):
                return jsonify({"mode": line.split("=")[1].strip()})
    
    return jsonify({"mode": "unknown"})

@app.route('/api/toggle_mode', methods=['POST'])
def toggle_mode():
    """Toggle the trading mode between paper and live."""
    env_path = Path("config/.env")
    if not env_path.exists():
        return jsonify({"error": ".env not found"}), 404
    
    current_mode = "unknown"
    new_mode = "paper"
    
    with open(env_path, "r") as f:
        lines = f.readlines()
    
    with open(env_path, "w") as f:
        for line in lines:
            if line.startswith("MODE="):
                current_mode = line.split("=")[1].strip()
                new_mode = "live" if current_mode == "paper" else "paper"
                f.write(f"MODE={new_mode}\n")
            else:
                f.write(line)
    
    return jsonify({"success": True, "old_mode": current_mode, "new_mode": new_mode})

if __name__ == '__main__':
    print("=" * 60)
    print("POLYMARKET BOT DASHBOARD")
    print("=" * 60)
    print("Open http://localhost:5555 in your browser")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5555, debug=False)
