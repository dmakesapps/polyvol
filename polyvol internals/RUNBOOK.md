# Deployment & Operations Runbook

## Overview

This document covers:
1. Local development setup
2. VPS deployment
3. Monitoring and alerting
4. Troubleshooting
5. Graduating to live trading

---

## Phase 1: Local Development

### Prerequisites

- Python 3.11+
- Git
- ~500MB disk space
- Internet connection

### Setup Steps

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/polymarket-evolution.git
cd polymarket-evolution

# 2. Create virtual environment
python3.11 -m venv venv

# 3. Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy environment template
cp config/.env.example config/.env

# 6. Edit .env with your settings
nano config/.env  # or use your preferred editor
```

### Environment Variables

```bash
# config/.env

# === Required ===
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx

# === Optional ===
LLM_MODEL=anthropic/claude-3-sonnet
DATABASE_PATH=data/evolution.db
LOG_LEVEL=INFO

# === Alerting (optional) ===
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx

# === Live Trading (Phase 4 only) ===
POLYMARKET_PRIVATE_KEY=
POLYMARKET_FUNDER_ADDRESS=
```

### Initialize Database

```bash
python scripts/init_db.py
```

### Running Locally

**Option A: Run everything (recommended for testing)**
```bash
python main.py
```

**Option B: Run components separately (for debugging)**

Terminal 1 - Price Collector:
```bash
python scripts/run_collector.py
```

Terminal 2 - Strategy Runner:
```bash
python scripts/run_strategies.py
```

Terminal 3 - Analysis (manual):
```bash
python scripts/run_analysis.py
```

### Verifying It Works

```bash
# Check database has data
python -c "
import sqlite3
conn = sqlite3.connect('data/evolution.db')
print('Prices:', conn.execute('SELECT COUNT(*) FROM prices').fetchone()[0])
print('Trades:', conn.execute('SELECT COUNT(*) FROM trades').fetchone()[0])
print('Strategies:', conn.execute('SELECT COUNT(*) FROM strategies').fetchone()[0])
"

# Check logs
tail -f logs/polymarket.log
```

---

## Phase 2: Validation

### Success Criteria

Before deploying to VPS, confirm:

- [ ] Price collector runs for 24+ hours without crashing
- [ ] At least 10 strategies are running
- [ ] At least 100 trades recorded
- [ ] Analysis reports generate correctly
- [ ] LLM integration works (test with manual call)

### Testing LLM Integration

```bash
python scripts/test_llm.py
```

This will:
1. Generate a sample report
2. Call the LLM
3. Parse the response
4. Display suggestions

### Reviewing Data

```bash
# Export recent trades to CSV for review
python scripts/export_trades.py --last 24h --output trades.csv

# Generate performance summary
python scripts/run_analysis.py --summary
```

---

## Phase 3: VPS Deployment

### Recommended VPS Providers

| Provider | Specs | Cost | Notes |
|----------|-------|------|-------|
| DigitalOcean | 1GB RAM, 1 CPU | $6/mo | Good starter option |
| Vultr | 1GB RAM, 1 CPU | $6/mo | Similar to DO |
| Hetzner | 2GB RAM, 2 CPU | $4/mo | Best value, EU-based |
| AWS Lightsail | 1GB RAM, 1 CPU | $5/mo | If you prefer AWS |

**Recommendation:** Start with DigitalOcean or Hetzner.

### VPS Setup

```bash
# SSH into your VPS
ssh root@YOUR_VPS_IP

# Update system
apt update && apt upgrade -y

# Install Python 3.11
apt install python3.11 python3.11-venv python3-pip git -y

# Create non-root user (recommended)
adduser polymarket
usermod -aG sudo polymarket
su - polymarket

# Clone repository
git clone https://github.com/YOUR_USERNAME/polymarket-evolution.git
cd polymarket-evolution

# Setup (same as local)
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy your .env file
nano config/.env  # Paste your config

# Initialize database
python scripts/init_db.py

# Test run
python main.py
# Ctrl+C after verifying it starts
```

### Systemd Service

Create a service file for automatic startup and restart:

```bash
sudo nano /etc/systemd/system/polymarket.service
```

```ini
[Unit]
Description=Polymarket Evolution Trading System
After=network.target

[Service]
Type=simple
User=polymarket
WorkingDirectory=/home/polymarket/polymarket-evolution
Environment="PATH=/home/polymarket/polymarket-evolution/venv/bin"
ExecStart=/home/polymarket/polymarket-evolution/venv/bin/python main.py
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/home/polymarket/polymarket-evolution/logs/service.log
StandardError=append:/home/polymarket/polymarket-evolution/logs/service.log

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable polymarket
sudo systemctl start polymarket

# Check status
sudo systemctl status polymarket

# View logs
journalctl -u polymarket -f
```

### Docker Deployment (Alternative)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  polymarket:
    build: .
    restart: always
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    env_file:
      - config/.env
```

```bash
# Deploy with Docker
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## Monitoring & Alerting

### Health Checks

The system performs automatic health checks:

1. **Price feed alive**: Checks if new prices received in last 5 minutes
2. **Database writable**: Confirms database operations work
3. **Strategy runner active**: Verifies strategies are executing
4. **API connectivity**: Tests Polymarket API access

### Discord Alerts

Setup Discord webhook for alerts:

1. Create a Discord server (or use existing)
2. Server Settings → Integrations → Webhooks → New Webhook
3. Copy webhook URL to `.env`:

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/xxx
```

Alerts sent for:
- 🚨 System errors
- ⚠️ Win rate drops below 60%
- 🏆 Strategy hits 75%+ win rate
- 📊 Daily performance summary
- 🔄 LLM evolution cycle completed

### Telegram Alerts (Alternative)

1. Create bot via @BotFather
2. Get chat ID via @userinfobot
3. Add to `.env`:

```bash
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx
```

### Manual Health Check

```bash
# SSH into VPS
ssh polymarket@YOUR_VPS_IP

# Check service status
sudo systemctl status polymarket

# Check recent logs
tail -100 logs/polymarket.log

# Check database stats
python -c "
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('data/evolution.db')

# Recent prices
recent = conn.execute('''
    SELECT COUNT(*) FROM prices 
    WHERE timestamp > datetime('now', '-1 hour')
''').fetchone()[0]
print(f'Prices (last hour): {recent}')

# Recent trades
trades = conn.execute('''
    SELECT COUNT(*) FROM trades 
    WHERE entry_time > datetime('now', '-24 hours')
''').fetchone()[0]
print(f'Trades (last 24h): {trades}')

# Strategy performance
print('\nStrategy Performance:')
for row in conn.execute('''
    SELECT s.id, s.status, 
           COUNT(t.id) as trades,
           AVG(CASE WHEN t.is_win THEN 1.0 ELSE 0.0 END) as win_rate
    FROM strategies s
    LEFT JOIN trades t ON s.id = t.strategy_id
    GROUP BY s.id
    ORDER BY win_rate DESC
    LIMIT 5
'''):
    print(f'  {row[0]}: {row[2]} trades, {row[3]*100:.1f}% WR')
"
```

### Performance Dashboard

Access via web (if enabled):

```
http://YOUR_VPS_IP:8080/dashboard
```

Or generate static report:

```bash
python scripts/generate_report.py --output report.html
# Download report.html to view locally
```

---

## Troubleshooting

### Common Issues

#### Price feed not receiving data

```bash
# Check if Polymarket API is accessible
curl -s https://gamma-api.polymarket.com/markets | head -100

# Check WebSocket connection
python -c "
import asyncio
import websockets
async def test():
    async with websockets.connect('wss://ws-subscriptions-clob.polymarket.com/ws/market') as ws:
        print('Connected!')
asyncio.run(test())
"
```

**Solutions:**
- Check internet connectivity
- Verify API endpoints haven't changed
- Check for IP blocking (try VPN)

#### Database locked

```bash
# Check for stuck processes
ps aux | grep python

# Kill stuck process if needed
kill -9 PID

# Check database integrity
python -c "
import sqlite3
conn = sqlite3.connect('data/evolution.db')
print(conn.execute('PRAGMA integrity_check').fetchone())
"
```

#### LLM API errors

```bash
# Test OpenRouter directly
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"anthropic/claude-3-sonnet","messages":[{"role":"user","content":"Hi"}]}'
```

**Solutions:**
- Check API key is valid
- Verify account has credits
- Check model name is correct

#### High memory usage

```bash
# Check memory
free -h

# Check process memory
ps aux --sort=-%mem | head -5
```

**Solutions:**
- Increase VPS RAM
- Add swap space:
  ```bash
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```

### Recovery Procedures

#### Restart service

```bash
sudo systemctl restart polymarket
```

#### Reset database (CAUTION: loses all data)

```bash
sudo systemctl stop polymarket
rm data/evolution.db
python scripts/init_db.py
sudo systemctl start polymarket
```

#### Rollback to previous version

```bash
sudo systemctl stop polymarket
git stash  # Save local changes
git checkout v1.0.0  # Or specific commit
pip install -r requirements.txt
sudo systemctl start polymarket
```

---

## Phase 4: Live Trading

### Requirements Before Going Live

- [ ] Paper trading running stable for 7+ days
- [ ] At least ONE strategy with 75%+ win rate over 500+ trades
- [ ] Win rate consistency (doesn't drop below 70% for >24h)
- [ ] All systems monitored with alerts
- [ ] Emergency stop procedure tested

### Wallet Setup

1. **Create new wallet** (don't use your main wallet)
2. **Fund with small amount** ($50-100 max to start)
3. **Export private key** (keep secure!)
4. **Add to .env:**

```bash
POLYMARKET_PRIVATE_KEY=0x...
POLYMARKET_FUNDER_ADDRESS=0x...
```

### Risk Limits

Configure in `config/settings.yaml`:

```yaml
live_trading:
  enabled: false  # Change to true when ready
  
  risk_limits:
    max_position_size_usd: 10
    max_daily_loss_usd: 20
    max_concurrent_positions: 3
    min_balance_usd: 50
    max_loss_streak: 5
    
  allowed_strategies:
    - deep_10_20  # Only promote tested strategies
    - deep_10_25
```

### Enabling Live Trading

```bash
# Edit settings
nano config/settings.yaml
# Set live_trading.enabled: true

# Restart service
sudo systemctl restart polymarket

# Monitor closely!
journalctl -u polymarket -f
```

### Emergency Stop

```bash
# Method 1: Stop service
sudo systemctl stop polymarket

# Method 2: Run emergency script
python scripts/emergency_stop.py

# Method 3: Disable in config
sed -i 's/enabled: true/enabled: false/' config/settings.yaml
sudo systemctl restart polymarket
```

---

## Maintenance

### Daily Tasks

- [ ] Check Discord/Telegram for alerts
- [ ] Review overnight performance
- [ ] Verify system is running

### Weekly Tasks

- [ ] Review LLM suggestions
- [ ] Check win rates across strategies
- [ ] Backup database
- [ ] Review and rotate logs

### Monthly Tasks

- [ ] Full system audit
- [ ] Update dependencies
- [ ] Review and optimize strategies
- [ ] Cost analysis (API usage, VPS)

### Backup Procedure

```bash
# Backup database
cp data/evolution.db backups/evolution_$(date +%Y%m%d).db

# Backup to remote (optional)
rsync -av data/evolution.db user@backup-server:/backups/
```

### Log Rotation

Add to `/etc/logrotate.d/polymarket`:

```
/home/polymarket/polymarket-evolution/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## Quick Reference

### Commands Cheat Sheet

```bash
# Service management
sudo systemctl start polymarket
sudo systemctl stop polymarket
sudo systemctl restart polymarket
sudo systemctl status polymarket

# View logs
journalctl -u polymarket -f
tail -f logs/polymarket.log

# Database queries
sqlite3 data/evolution.db "SELECT COUNT(*) FROM trades"
sqlite3 data/evolution.db ".schema"

# Manual analysis
python scripts/run_analysis.py
python scripts/run_analysis.py --strategy deep_10_20

# LLM evolution (manual)
python scripts/run_evolution.py

# Export data
python scripts/export_trades.py --output trades.csv

# Emergency stop
python scripts/emergency_stop.py
```

### Important File Locations

| File | Purpose |
|------|---------|
| `config/.env` | API keys and secrets |
| `config/settings.yaml` | System configuration |
| `config/strategies.yaml` | Strategy definitions |
| `data/evolution.db` | Main database |
| `logs/polymarket.log` | Application logs |
| `data/llm_logs/` | LLM interaction history |

### Support

- GitHub Issues: [link]
- Discord: [link]
- Email: [email]

---

*Document Version: 1.0*
*Last Updated: January 2025*
