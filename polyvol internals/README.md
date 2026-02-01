# Polymarket Evolution System

**Goal: Achieve 75%+ win rate trading Polymarket 15-minute crypto markets**

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/polymarket-evolution.git
cd polymarket-evolution

# Setup
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp config/.env.example config/.env
# Edit .env with your OpenRouter API key

# Initialize
python scripts/init_db.py

# Run
python main.py
```

## What This Does

1. **Collects** real-time price data from Polymarket's 15-minute BTC up/down markets
2. **Runs** 15+ trading strategies simultaneously (paper trading)
3. **Analyzes** which strategies achieve 75%+ win rate
4. **Evolves** strategies using LLM-powered insights (Claude/GPT-4)

## The Strategy

We're not predicting if BTC goes up or down. We're trading **volatility**:

- Buy YES when it drops to 10-20% (oversold)
- Sell when it bounces to 20-30% (profit)
- We only need 50-60% win rate due to favorable math

## Documentation

| Document | Description |
|----------|-------------|
| [OVERVIEW.md](docs/OVERVIEW.md) | Full system documentation |
| [STRATEGIES.md](docs/STRATEGIES.md) | All strategy specifications |
| [LLM_INTEGRATION.md](docs/LLM_INTEGRATION.md) | OpenRouter setup |
| [RUNBOOK.md](docs/RUNBOOK.md) | Deployment & operations |

## Development Phases

1. **Build Locally** → Validate system works
2. **Paper Trade** → Find winning strategies
3. **Deploy to VPS** → 24/7 operation
4. **Live Trading** → Real profits

## Key Insight

Lower entry prices = more forgiving math:

| Strategy | Break-Even Win Rate |
|----------|---------------------|
| 10% → 20% | 50% |
| 10% → 25% | 40% |
| 20% → 25% | 80% |
| 40% → 50% | 80% |

**Focus on Tier 1 (Deep Value) strategies first.**

## License

MIT

## Disclaimer

This is experimental trading software. Use at your own risk. Start with paper trading and small amounts.
