# Polymarket Volatility Trading Bot

**Goal: Achieve 75%+ win rate trading 15-minute crypto markets on Polymarket**

## Quick Start

```bash
# 1. Setup virtual environment
cd /Users/davis/Desktop/polyvol/polyvol
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment template (optional - no keys needed for paper trading)
cp config/.env.example config/.env

# 4. Initialize database
python scripts/init_db.py

# 5. Run the bot!
python main.py
```

## What It Does

1. **Discovers** active 15-minute BTC/ETH up/down markets on Polymarket
2. **Collects** real-time price data (no API key required)
3. **Runs** 18 strategies simultaneously (paper trading)
4. **Tracks** every trade with full context in SQLite
5. **Reports** win rates and performance metrics

## The Core Strategy

We're NOT predicting if BTC goes up or down. We're trading **volatility bounces**:

- Buy when one side drops to an extreme (10-20%)
- Sell when it bounces back (20-30%)
- The math is heavily in our favor at lower entry prices

### Why Lower Entries Are Better

| Entry → Exit | Profit if Win | Break-Even WR | Assessment |
|--------------|---------------|---------------|------------|
| 5% → 15% | +200% | **33%** | ⭐ Best math |
| 10% → 20% | +100% | **50%** | ⭐ Recommended |
| 20% → 25% | +25% | **80%** | ❌ Risky |

## Files

```
polyvol/
├── config/
│   ├── .env.example      # API keys (optional)
│   └── settings.yaml     # All strategy configs
├── data/
│   └── evolution.db      # SQLite database (auto-created)
├── src/
│   ├── core/             # Config, models, database
│   ├── collection/       # Polymarket API clients
│   ├── strategies/       # Trading strategies
│   ├── analysis/         # Metrics & reporting
│   └── bankroll/         # Position sizing
├── scripts/
│   ├── init_db.py        # Initialize database
│   └── run_analysis.py   # Generate reports
├── main.py               # Run the bot
└── requirements.txt
```

## Commands

```bash
# Run the bot
python main.py

# Generate performance report
python scripts/run_analysis.py

# Generate report for last 24 hours
python scripts/run_analysis.py --hours 24

# JSON output (for LLM analysis)
python scripts/run_analysis.py --json
```

## API Keys

| Phase | Keys Needed |
|-------|-------------|
| **Paper Trading** | None! Works out of the box |
| **LLM Evolution** | OpenRouter key (optional) |
| **Live Trading** | Polymarket wallet (later) |

## Next Steps

1. Run `python main.py` and let it collect data
2. Wait for entries on Tier 1 strategies (10-20% prices)
3. After 50+ trades, check win rates with `python scripts/run_analysis.py`
4. Goal: Find a strategy with 75%+ win rate over 200+ trades

## License

MIT
