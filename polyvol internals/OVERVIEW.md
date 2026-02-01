# Polymarket Volatility Trading System

## Mission Statement

**Goal: Achieve and maintain a 75%+ win rate trading 15-minute crypto prediction markets on Polymarket.**

We are not predicting whether BTC goes up or down. We are exploiting **price volatility** within the 15-minute window - buying when one side drops to an extreme and selling when it bounces back.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Concept](#core-concept)
3. [Strategy Framework](#strategy-framework)
4. [Technical Architecture](#technical-architecture)
5. [Data Schema](#data-schema)
6. [LLM Integration](#llm-integration)
7. [Deployment Guide](#deployment-guide)
8. [Risk Management](#risk-management)
9. [Success Metrics](#success-metrics)

---

## System Overview

### What We're Building

A 24/7 automated system that:

1. **Collects** real-time price data from Polymarket's 15-minute crypto markets
2. **Runs** multiple trading strategies simultaneously (paper trading)
3. **Stores** every trade with full context for analysis
4. **Analyzes** performance to find winning strategies
5. **Evolves** strategies using LLM-powered insights
6. **Graduates** proven strategies to live trading

### Development Phases

| Phase | Description | Duration | Milestone |
|-------|-------------|----------|-----------|
| **Phase 1** | Build locally | 1-2 weeks | Working paper trading system |
| **Phase 2** | Validate | 2-4 weeks | Identify strategy with 75%+ WR |
| **Phase 3** | Deploy to VPS | 1 week | 24/7 operation |
| **Phase 4** | Live trading | Ongoing | Real profits |

---

## Core Concept

### The Market Mechanics

Polymarket's 15-minute BTC Up/Down markets work as follows:

- Market opens with YES and NO prices (always sum to 100%)
- Prices fluctuate based on trading activity and BTC price movement
- After 15 minutes, market resolves:
  - If BTC went UP: YES = 100%, NO = 0%
  - If BTC went DOWN: YES = 0%, NO = 100%

**Critical Insight:** There is NO middle ground at resolution. Every position either goes to 100% (full win) or 0% (total loss).

### Resolution Volatility Phenomenon

**As markets approach resolution, price movements become EXTREME.**

```
TIME REMAINING    PRICE BEHAVIOR
────────────────────────────────────────────────────────────────
15-10 min         Normal oscillation, mean reversion works
10-5 min          Volatility increases, trends start forming
5-2 min           EXTREME moves, panic selling/buying
2-0 min           Rush to 0% or 100%, no time for reversal
```

**Why this matters:**
1. Ultra-deep entries (5-10%) often happen in final minutes as one side collapses
2. The "dead" side sometimes makes miraculous comebacks if BTC reverses
3. Our BEST risk/reward entries (5%→15% = +200%) appear during resolution panic
4. Time filters can improve win rate by targeting specific phases

### Our Edge

We're not predicting BTC direction. We're exploiting the fact that:

1. Prices are highly volatile within the 15-minute window
2. Extreme prices (10%, 20%, 80%, 90%) often revert toward the middle
3. We can capture profit from the BOUNCE without holding to resolution

### The Trade

```
Example: Buy YES at 20%

Scenario A - Bounce (WE WIN):
  Price: 20% → 25% → 30% → we exit at 25%
  Profit: +25%
  
Scenario B - No Bounce (WE LOSE):
  Price: 20% → 15% → 10% → 5% → 0% (resolution)
  Loss: -100%

Key: We need bounces to happen MORE than 80% of the time
     for a 20%→25% strategy to be profitable.
```

### Why Lower Entries Are Better

| Entry Price | Exit Price | Profit if Win | Break-Even Win Rate | Assessment |
|-------------|------------|---------------|---------------------|------------|
| **5%** | **10%** | **+100%** | **50%** | ⭐ SUPER STRATEGY |
| **5%** | **15%** | **+200%** | **33%** | ⭐ SUPER STRATEGY |
| **5%** | **20%** | **+300%** | **25%** | ⭐ Best math possible |
| 10% | 20% | +100% | 50% | Recommended |
| 10% | 25% | +150% | 40% | Recommended |
| 15% | 25% | +67% | 60% | Good balance |
| 20% | 25% | +25% | 80% | Original idea - risky |
| 40% | 50% | +25% | 80% | Needs high WR |
| 80% | 90% | +12.5% | 89% | Dangerous |

**The 5%→15% strategy only needs to win 1 out of 3 trades to break even!**

**Lower entries = more forgiving math = higher chance of profitability**

**Note:** 5% entries are rare but often occur during resolution volatility when one side is collapsing in the final minutes.

---

## Strategy Framework

### Strategy Types

We categorize strategies by entry price range:

#### Tier 1: Deep Value (Entry 10-20%)

**Highest probability of profitability**

| Strategy ID | Entry | Exit | Profit/Win | Break-Even WR | Notes |
|-------------|-------|------|------------|---------------|-------|
| `deep_10_15` | 10% | 15% | +50% | 67% | Small bounce target |
| `deep_10_20` | 10% | 20% | +100% | 50% | **RECOMMENDED** |
| `deep_10_25` | 10% | 25% | +150% | 40% | **RECOMMENDED** |
| `deep_15_20` | 15% | 20% | +33% | 75% | Moderate |
| `deep_15_25` | 15% | 25% | +67% | 60% | **RECOMMENDED** |
| `deep_15_30` | 15% | 30% | +100% | 50% | Let it run |

**Why these work:** Only need 40-60% win rate. When price is at 10-15%, it's often oversold and bounces back. Even if we're wrong 50% of the time, the +100% wins cover the -100% losses.

#### Tier 2: Value (Entry 20-35%)

**Moderate probability, test to validate**

| Strategy ID | Entry | Exit | Profit/Win | Break-Even WR | Notes |
|-------------|-------|------|------------|---------------|-------|
| `value_20_25` | 20% | 25% | +25% | 80% | Original idea - RISKY |
| `value_20_30` | 20% | 30% | +50% | 67% | Better math |
| `value_20_35` | 20% | 35% | +75% | 57% | Even better |
| `value_25_30` | 25% | 30% | +20% | 83% | Tight, risky |
| `value_25_35` | 25% | 35% | +40% | 71% | Moderate |
| `value_30_40` | 30% | 40% | +33% | 75% | Moderate |

**Why riskier:** Need 67-80% win rate. The math is less forgiving.

#### Tier 3: Mid-Range Reversion (Entry 35-50%)

**High frequency, needs high win rate**

| Strategy ID | Entry | Exit | Profit/Win | Break-Even WR | Notes |
|-------------|-------|------|------------|---------------|-------|
| `mid_35_45` | 35% | 45% | +29% | 78% | Common entry |
| `mid_35_50` | 35% | 50% | +43% | 70% | Worth testing |
| `mid_40_50` | 40% | 50% | +25% | 80% | Very common |
| `mid_40_55` | 40% | 55% | +38% | 73% | Worth testing |
| `mid_45_50` | 45% | 50% | +11% | 90% | Tight, dangerous |
| `mid_45_55` | 45% | 55% | +22% | 82% | Risky |

**Trade-off:** These entries happen frequently, but you need 70-80%+ win rates.

#### Tier 4: High Probability (Entry 55-75%)

**Betting on continuation, not reversal**

| Strategy ID | Entry | Exit | Profit/Win | Break-Even WR | Notes |
|-------------|-------|------|------------|---------------|-------|
| `high_55_65` | 55% | 65% | +18% | 85% | Needs high WR |
| `high_60_70` | 60% | 70% | +17% | 86% | Risky |
| `high_65_75` | 65% | 75% | +15% | 87% | Very risky |
| `high_70_80` | 70% | 80% | +14% | 88% | Dangerous |

**Reality check:** You need 85%+ win rate. One loss wipes out 6-7 wins.

#### Tier 5: Fade the Extreme (Entry 75-90%)

**Contrarian - betting the favorite fails**

| Strategy ID | Entry | Exit | Profit/Win | Break-Even WR | Notes |
|-------------|-------|------|------------|---------------|-------|
| `fade_75_65` | 75% | 65% | +15% | 87% | Counter-trend |
| `fade_80_70` | 80% | 70% | +14% | 88% | Risky |
| `fade_85_75` | 85% | 75% | +13% | 88% | Very risky |
| `fade_90_80` | 90% | 80% | +12.5% | 89% | Dangerous |

**Note:** "Fade" means we're buying the OTHER side. If YES is at 80%, we buy NO at 20%.

### Recommended Starting Portfolio

Run these simultaneously to gather data:

```python
INITIAL_STRATEGIES = [
    # ULTRA-DEEP - Best math, rare entries (resolution volatility)
    {"id": "ultra_05_10", "entry": 0.05, "exit": 0.10, "tier": 1},  # ⭐ SUPER
    {"id": "ultra_05_15", "entry": 0.05, "exit": 0.15, "tier": 1},  # ⭐ SUPER
    {"id": "ultra_05_20", "entry": 0.05, "exit": 0.20, "tier": 1},
    
    # PRIMARY - Most likely to profit
    {"id": "deep_10_20", "entry": 0.10, "exit": 0.20, "tier": 1},
    {"id": "deep_10_25", "entry": 0.10, "exit": 0.25, "tier": 1},
    {"id": "deep_15_25", "entry": 0.15, "exit": 0.25, "tier": 1},
    {"id": "deep_15_30", "entry": 0.15, "exit": 0.30, "tier": 1},
    
    # SECONDARY - Worth testing
    {"id": "value_20_30", "entry": 0.20, "exit": 0.30, "tier": 2},
    {"id": "value_20_35", "entry": 0.20, "exit": 0.35, "tier": 2},
    {"id": "mid_35_50", "entry": 0.35, "exit": 0.50, "tier": 3},
    {"id": "mid_40_55", "entry": 0.40, "exit": 0.55, "tier": 3},
    
    # CONTROL - Baseline comparison
    {"id": "value_20_25", "entry": 0.20, "exit": 0.25, "tier": 2},
    {"id": "mid_40_50", "entry": 0.40, "exit": 0.50, "tier": 3},
    {"id": "high_60_70", "entry": 0.60, "exit": 0.70, "tier": 4},
    
    # EXPERIMENTAL - Fade strategies
    {"id": "fade_80_70", "entry": 0.80, "exit": 0.70, "tier": 5},
    {"id": "fade_90_80", "entry": 0.90, "exit": 0.80, "tier": 5},
]
```

### Stop Loss Policy

**Recommendation: NO STOP LOSS**

Reasoning:
1. Markets resolve in 15 minutes - time naturally limits exposure
2. These markets are extremely volatile - stop losses get triggered constantly
3. A price at 10% can easily go to 5% then bounce to 25%
4. Stop losses turn paper losses into real losses

Instead, we use **time-based exits**:
- Exit if position is underwater with < 2 minutes to resolution
- Exit if held for > 10 minutes with no progress toward target

### Exit Rules (Priority Order)

```python
def should_exit(position, current_price, time_remaining):
    """
    Exit decision logic in priority order.
    """
    
    # 1. TAKE PROFIT - Price hit our target
    if current_price >= position.exit_target:
        return True, "TAKE_PROFIT"
    
    # 2. RESOLUTION IMMINENT - Exit before forced resolution
    if time_remaining < 120:  # < 2 minutes
        return True, "RESOLUTION_EXIT"
    
    # 3. TIME DECAY - Held too long without progress
    if position.hold_time > 600:  # > 10 minutes
        if current_price < position.entry_price:
            return True, "TIME_STOP"
    
    # 4. HOLD - Wait for target
    return False, None
```

### Hybrid Strategy (Future Enhancement)

For later implementation:

```
Entry: 10-15%
Exit Strategy:
  - Sell 50% at 25% (lock in profit)
  - Let remaining 50% ride to resolution

Benefits:
  - Guaranteed profit capture
  - Still exposed to 10% → 100% upside
  - Reduced risk while keeping upside
```

---

## Technical Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         POLYMARKET EVOLUTION SYSTEM                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    LAYER 1: DATA COLLECTION                    │ │
│  │                         (runs 24/7)                            │ │
│  │                                                                │ │
│  │   Polymarket WebSocket ──▶ Price Parser ──▶ SQLite Database   │ │
│  │                                                                │ │
│  │   Captures:                                                    │ │
│  │   • Every price tick (YES and NO)                             │ │
│  │   • Order book snapshots                                       │ │
│  │   • Market metadata (time remaining, volume)                  │ │
│  │   • Resolution outcomes                                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                 LAYER 2: MULTI-STRATEGY RUNNER                 │ │
│  │                         (runs 24/7)                            │ │
│  │                                                                │ │
│  │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │ │
│  │   │deep_10_20│ │deep_15_25│ │value_20  │ │mid_40_55 │  ...   │ │
│  │   │          │ │          │ │_30       │ │          │        │ │
│  │   └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │ │
│  │        │            │            │            │               │ │
│  │        └────────────┴────────────┴────────────┘               │ │
│  │                          │                                     │ │
│  │              All mock trades logged to DB                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    LAYER 3: DATA STORE                         │ │
│  │                        (SQLite)                                │ │
│  │                                                                │ │
│  │   Tables:                                                      │ │
│  │   • prices - Every price tick                                 │ │
│  │   • trades - Every mock trade with full context               │ │
│  │   • strategies - Strategy configs and metadata                │ │
│  │   • snapshots - Hourly performance aggregates                 │ │
│  │   • insights - LLM-generated insights                         │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                 LAYER 4: ANALYSIS ENGINE                       │ │
│  │                    (runs every hour)                           │ │
│  │                                                                │ │
│  │   • Calculate win rate per strategy                           │ │
│  │   • Statistical significance testing                          │ │
│  │   • Pattern detection (time of day, entry level, etc.)       │ │
│  │   • Generate performance reports                              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   LAYER 5: LLM ADVISOR                         │ │
│  │               (runs every 6-12 hours)                          │ │
│  │                                                                │ │
│  │   Input:  performance_report.json                             │ │
│  │                        │                                       │ │
│  │                        ▼                                       │ │
│  │              ┌─────────────────┐                              │ │
│  │              │   OpenRouter    │                              │ │
│  │              │   (Claude/GPT)  │                              │ │
│  │              └────────┬────────┘                              │ │
│  │                       │                                        │ │
│  │                       ▼                                        │ │
│  │   Output: strategy_suggestions.json                           │ │
│  │   • New strategies to test                                    │ │
│  │   • Strategies to retire                                      │ │
│  │   • Pattern insights                                          │ │
│  │   • Hypotheses to validate                                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  LAYER 6: STRATEGY EVOLVER                     │ │
│  │                                                                │ │
│  │   • Parse and validate LLM suggestions                        │ │
│  │   • Spawn new strategy instances                              │ │
│  │   • Retire underperforming strategies                         │ │
│  │   • Promote winners to "champion" status                      │ │
│  │   • Maintain strategy diversity                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### File Structure

```
polymarket_evolution/
│
├── docs/
│   ├── OVERVIEW.md              # This document
│   ├── STRATEGIES.md            # Detailed strategy documentation
│   ├── DATA_SCHEMA.md           # Database schema reference
│   ├── LLM_INTEGRATION.md       # OpenRouter setup and prompts
│   ├── DEPLOYMENT.md            # VPS deployment guide
│   └── RUNBOOK.md               # Operations manual
│
├── config/
│   ├── settings.yaml            # Main configuration
│   ├── strategies.yaml          # Strategy definitions
│   └── .env.example             # Environment variables template
│
├── data/
│   ├── evolution.db             # SQLite database
│   ├── price_cache/             # Raw price data backups
│   ├── reports/                 # Generated reports
│   └── llm_logs/                # LLM interaction history
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py          # Database operations
│   │   ├── models.py            # Data models (Trade, Strategy, etc.)
│   │   └── config.py            # Configuration loader
│   │
│   ├── collection/
│   │   ├── __init__.py
│   │   ├── polymarket_client.py # API client
│   │   ├── websocket_feed.py    # Real-time price feed
│   │   └── price_collector.py   # Price storage logic
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py              # Base strategy class
│   │   ├── volatility.py        # Volatility bounce strategies
│   │   ├── registry.py          # Strategy factory
│   │   └── runner.py            # Multi-strategy executor
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── metrics.py           # Performance calculations
│   │   ├── statistics.py        # Statistical tests
│   │   ├── patterns.py          # Pattern detection
│   │   └── reporter.py          # Report generation
│   │
│   ├── evolution/
│   │   ├── __init__.py
│   │   ├── llm_client.py        # OpenRouter integration
│   │   ├── prompts.py           # Prompt templates
│   │   ├── parser.py            # LLM response parser
│   │   └── evolver.py           # Strategy evolution logic
│   │
│   └── services/
│       ├── __init__.py
│       ├── scheduler.py         # Task scheduling
│       ├── alerting.py          # Notifications
│       └── monitoring.py        # Health checks
│
├── scripts/
│   ├── run_collector.py         # Start price collection
│   ├── run_strategies.py        # Start strategy runner
│   ├── run_analysis.py          # Run analysis manually
│   ├── run_evolution.py         # Run LLM evolution
│   └── run_all.py               # Start entire system
│
├── tests/
│   ├── test_strategies.py
│   ├── test_analysis.py
│   └── test_database.py
│
├── main.py                      # Entry point
├── requirements.txt             # Dependencies
├── Dockerfile                   # Container definition
├── docker-compose.yml           # Full stack deployment
└── README.md                    # Quick start guide
```

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.11+ | Main runtime |
| Database | SQLite | Data storage (simple, portable) |
| Price Feed | `websockets` | Real-time Polymarket data |
| HTTP Client | `httpx` | API calls (async) |
| Scheduling | `APScheduler` | Task scheduling |
| LLM | OpenRouter API | Strategy evolution |
| Config | YAML | Configuration management |
| Logging | `structlog` | Structured logging |
| Monitoring | Custom + Discord | Alerts and status |

---

## Data Schema

### prices table

Stores every price tick from Polymarket.

```sql
CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Market identification
    market_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    asset TEXT NOT NULL,              -- BTC, ETH, SOL, etc.
    
    -- Price data
    yes_price REAL NOT NULL,
    no_price REAL NOT NULL,
    
    -- Market state
    time_remaining REAL,              -- Seconds until resolution
    volume REAL,                       -- Market volume
    liquidity REAL,                    -- Available liquidity
    
    -- Metadata
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_prices_market (market_id),
    INDEX idx_prices_time (timestamp),
    INDEX idx_prices_asset (asset)
);
```

### trades table

Records every mock (and eventually real) trade.

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Strategy reference
    strategy_id TEXT NOT NULL,
    
    -- Market identification
    market_id TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    asset TEXT NOT NULL,
    
    -- Trade details
    side TEXT NOT NULL,               -- YES or NO
    entry_price REAL NOT NULL,
    exit_price REAL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    shares REAL NOT NULL,
    
    -- Outcome
    pnl REAL,
    pnl_pct REAL,
    is_win INTEGER,
    exit_reason TEXT,                 -- TAKE_PROFIT, RESOLUTION_EXIT, TIME_STOP, etc.
    
    -- Context for learning
    time_remaining_at_entry REAL,
    time_remaining_at_exit REAL,
    price_at_entry_1min_ago REAL,     -- For momentum analysis
    price_at_entry_5min_ago REAL,
    hour_of_day INTEGER,
    day_of_week INTEGER,
    
    -- Market conditions
    market_volatility REAL,           -- Calculated volatility
    book_depth_at_entry REAL,
    spread_at_entry REAL,
    
    -- Status
    status TEXT DEFAULT 'open',       -- open, closed
    is_paper INTEGER DEFAULT 1,       -- 1 = paper trade, 0 = real
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);
```

### strategies table

Stores strategy configurations and metadata.

```sql
CREATE TABLE strategies (
    id TEXT PRIMARY KEY,
    
    -- Configuration
    name TEXT NOT NULL,
    params TEXT NOT NULL,             -- JSON blob of parameters
    tier INTEGER,                     -- 1-5 strategy tier
    
    -- Lineage
    generation INTEGER DEFAULT 0,     -- Evolution generation
    parent_id TEXT,                   -- Which strategy it evolved from
    
    -- Status
    status TEXT DEFAULT 'active',     -- active, retired, champion, testing
    
    -- Performance cache
    total_trades INTEGER DEFAULT 0,
    win_rate REAL,
    total_pnl REAL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retired_at TIMESTAMP,
    
    FOREIGN KEY (parent_id) REFERENCES strategies(id)
);
```

### snapshots table

Hourly performance aggregates.

```sql
CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    strategy_id TEXT NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    period_type TEXT NOT NULL,        -- hour, day, week
    
    -- Metrics
    trades INTEGER,
    wins INTEGER,
    losses INTEGER,
    win_rate REAL,
    total_pnl REAL,
    avg_pnl REAL,
    
    -- Breakdown by exit reason
    take_profits INTEGER,
    resolution_exits INTEGER,
    time_stops INTEGER,
    
    -- Risk metrics
    max_drawdown REAL,
    sharpe_ratio REAL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);
```

### insights table

Stores LLM-generated insights and hypotheses.

```sql
CREATE TABLE insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Content
    insight_type TEXT NOT NULL,       -- pattern, hypothesis, recommendation
    content TEXT NOT NULL,
    confidence REAL,
    
    -- Validation
    tested INTEGER DEFAULT 0,
    validated INTEGER DEFAULT 0,
    test_result TEXT,
    
    -- Source
    llm_model TEXT,
    prompt_hash TEXT,                 -- For deduplication
    
    -- Metadata
    metadata TEXT,                    -- JSON blob
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## LLM Integration

### OpenRouter Setup

We use OpenRouter to access multiple LLM providers with one API.

**Recommended Models:**
- `anthropic/claude-3-opus` - Best reasoning, use for complex analysis
- `anthropic/claude-3-sonnet` - Good balance, use for routine analysis
- `openai/gpt-4-turbo` - Alternative, good for structured output

### LLM Advisor Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM ADVISOR CYCLE                        │
│                  (runs every 6-12 hours)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. GENERATE REPORT                                         │
│     │                                                       │
│     ├── Query database for last 6-12 hours                 │
│     ├── Calculate metrics per strategy                     │
│     ├── Identify patterns                                  │
│     └── Format as structured JSON                          │
│                                                             │
│  2. BUILD PROMPT                                            │
│     │                                                       │
│     ├── System context (who we are, what we want)          │
│     ├── Performance data                                   │
│     ├── Trade log sample                                   │
│     ├── Pattern analysis                                   │
│     └── Specific questions                                 │
│                                                             │
│  3. CALL LLM                                                │
│     │                                                       │
│     └── OpenRouter API → Claude/GPT                        │
│                                                             │
│  4. PARSE RESPONSE                                          │
│     │                                                       │
│     ├── Extract JSON from response                         │
│     ├── Validate suggested parameters                      │
│     └── Check against bounds                               │
│                                                             │
│  5. APPLY CHANGES                                           │
│     │                                                       │
│     ├── Spawn new strategies                               │
│     ├── Retire underperformers                             │
│     ├── Update strategy priorities                         │
│     └── Log all changes                                    │
│                                                             │
│  6. AUDIT                                                   │
│     │                                                       │
│     └── Save prompt, response, and actions to database     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Master Prompt Template

```markdown
# SYSTEM

You are a world-class quantitative trader specializing in Polymarket volatility strategies.
Your goal is to help achieve and maintain a 75%+ win rate.

You analyze empirical trading data and suggest strategy improvements based on evidence.
You are precise, data-driven, and skeptical of unproven hypotheses.

# CONTEXT

## How Our System Works

We trade Polymarket's 15-minute BTC up/down markets.
- Markets resolve to either 100/0 or 0/100 (no middle ground)
- We buy one side when it drops to a low price (e.g., 20%)
- We sell when it bounces back (e.g., to 25%)
- We're trading VOLATILITY, not predicting BTC direction

## Key Metrics

- **Win Rate**: % of trades that hit target (we need 75%+)
- **Break-Even WR**: Win rate needed to not lose money
- **Profit Factor**: Gross profit / Gross loss

## Strategy Tiers

- **Tier 1 (Deep Value)**: Entry 10-20%, need 40-60% WR
- **Tier 2 (Value)**: Entry 20-35%, need 60-75% WR
- **Tier 3 (Mid-Range)**: Entry 35-50%, need 70-80% WR
- **Tier 4 (High Prob)**: Entry 55-75%, need 85%+ WR
- **Tier 5 (Fade)**: Entry 75-90%, need 87%+ WR

# CURRENT DATA

## Strategy Performance (Last {period})

{strategy_performance_table}

## Recent Trades (Last 50)

{recent_trades_table}

## Pattern Analysis

### By Entry Price
{entry_price_analysis}

### By Time of Day (UTC)
{time_of_day_analysis}

### By Time Remaining at Entry
{time_remaining_analysis}

### By Exit Reason
{exit_reason_breakdown}

# YOUR TASK

Analyze this data and provide:

1. **Performance Analysis**: Why are some strategies outperforming others?

2. **Pattern Insights**: What patterns correlate with wins vs losses?

3. **New Strategies**: Suggest 2-3 new strategies to test with specific parameters.
   - Parameters must be within bounds: entry 0.05-0.50, exit 0.10-0.95
   - Include your hypothesis for why it might work

4. **Retirement Recommendations**: Which strategies should we stop running?
   - Only retire strategies with 100+ trades
   - Must be statistically significantly worse than baseline

5. **Next Experiment**: What hypothesis should we test next?

# OUTPUT FORMAT

Respond in valid JSON:

```json
{
  "analysis": {
    "summary": "One paragraph summary of findings",
    "top_performer": "strategy_id with reasoning",
    "concerning": "Any strategies or patterns that concern you"
  },
  "patterns": [
    {
      "pattern": "Description of pattern",
      "evidence": "Data that supports this",
      "actionable": "How to exploit or avoid this"
    }
  ],
  "new_strategies": [
    {
      "id": "descriptive_name",
      "entry": 0.XX,
      "exit": 0.XX,
      "tier": N,
      "hypothesis": "Why this might work",
      "expected_wr": "XX-XX%"
    }
  ],
  "retire": ["strategy_id_1", "strategy_id_2"],
  "promote": "strategy_id_to_promote_to_champion",
  "next_experiment": {
    "hypothesis": "What to test",
    "method": "How to test it",
    "success_criteria": "How we know it worked"
  }
}
```
```

### Guardrails

To prevent the LLM from making bad suggestions:

```python
PARAMETER_BOUNDS = {
    "entry": {"min": 0.05, "max": 0.50},   # 5% to 50%
    "exit": {"min": 0.10, "max": 0.95},    # 10% to 95%
    "exit_must_be_greater_than_entry": True,
    "min_spread": 0.05,                     # At least 5% difference
}

EVOLUTION_RULES = {
    "min_trades_before_retire": 100,
    "min_trades_before_promote": 200,
    "max_strategies_active": 25,
    "min_strategies_active": 5,
    "require_statistical_significance": True,
    "confidence_threshold": 0.95,           # 95% confidence for decisions
}
```

---

## Deployment Guide

### Phase 1: Local Development

```bash
# Clone repo
git clone <repo>
cd polymarket_evolution

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp config/.env.example config/.env
# Edit .env with your API keys

# Initialize database
python scripts/init_db.py

# Run tests
pytest tests/

# Start price collection (terminal 1)
python scripts/run_collector.py

# Start strategy runner (terminal 2)
python scripts/run_strategies.py

# Run analysis manually
python scripts/run_analysis.py
```

### Phase 2: VPS Deployment

**Recommended VPS:**
- DigitalOcean Droplet ($6-12/month)
- 1GB RAM, 1 CPU is sufficient
- Ubuntu 22.04 LTS

```bash
# On VPS
sudo apt update && sudo apt upgrade -y
sudo apt install python3.11 python3.11-venv python3-pip -y

# Clone and setup (same as local)
git clone <repo>
cd polymarket_evolution
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup as systemd service
sudo cp deploy/polymarket.service /etc/systemd/system/
sudo systemctl enable polymarket
sudo systemctl start polymarket

# Check status
sudo systemctl status polymarket
journalctl -u polymarket -f  # Follow logs
```

### Docker Deployment (Alternative)

```bash
# Build
docker build -t polymarket-evolution .

# Run
docker-compose up -d

# Logs
docker-compose logs -f
```

---

## Risk Management

### Paper Trading Phase

- All trades are simulated
- No real money at risk
- Goal: Validate strategy achieves 75%+ win rate over 500+ trades

### Graduating to Live

**Requirements before live trading:**

1. ✅ Strategy has 75%+ win rate over 500+ paper trades
2. ✅ Win rate is consistent (doesn't drop below 70% for >24 hours)
3. ✅ Positive expected value confirmed
4. ✅ Strategy works across different market conditions
5. ✅ System has been running stable for 1+ week

### Live Trading Limits

```python
RISK_LIMITS = {
    "max_position_size_usd": 10,        # Start small
    "max_daily_loss_usd": 20,           # Stop if down $20
    "max_concurrent_positions": 3,
    "min_balance_usd": 50,              # Don't trade if below $50
    "max_loss_streak": 5,               # Pause after 5 consecutive losses
}
```

### Emergency Procedures

**Kill Switch:**
```bash
# Stop all trading immediately
python scripts/emergency_stop.py
```

**Manual Override:**
```bash
# Force exit all positions
python scripts/force_exit_all.py
```

---

## Success Metrics

### Primary Goal

**75%+ win rate sustained over 500+ trades**

### Tracking Dashboard

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Overall Win Rate | ≥75% | --% | 🔴 |
| Trades (Total) | ≥500 | -- | 🔴 |
| Best Strategy WR | ≥75% | --% | 🔴 |
| Profit Factor | ≥1.5 | -- | 🔴 |
| Max Drawdown | ≤20% | --% | 🔴 |

### Milestones

| Milestone | Criteria | Reward |
|-----------|----------|--------|
| 🏁 First Trade | System executes first paper trade | System works |
| 📊 100 Trades | Any strategy reaches 100 trades | Enough data to analyze |
| 🎯 70% WR | Any strategy hits 70% win rate | Getting close |
| ⭐ 75% WR | Any strategy hits 75% win rate | **PRIMARY GOAL** |
| 🏆 Champion | Strategy sustains 75%+ over 500 trades | Ready for live |
| 💰 Live Profit | First profitable week of live trading | Real money made |

---

## Position Sizing & Bankroll Management

**See [BANKROLL_MANAGEMENT.md](BANKROLL_MANAGEMENT.md) for complete documentation.**

### The Kelly Criterion

The optimal bet size is determined by:

```
Kelly % = Win Rate - [(1 - Win Rate) / R Ratio]

Where R Ratio = Average Win / Average Loss
```

### Kelly Values for Our Strategies

| Strategy | Est. Win Rate | Profit | Kelly % | Half Kelly | Verdict |
|----------|---------------|--------|---------|------------|---------|
| **ultra_05_15** | 45% | +200% | **17.5%** | 8.75% | ⭐ GREAT |
| **ultra_05_10** | 55% | +100% | **10.0%** | 5.0% | ⭐ GREAT |
| **deep_10_20** | 60% | +100% | **20.0%** | 10.0% | ⭐ GREAT |
| **deep_10_25** | 55% | +150% | **25.0%** | 12.5% | ⭐ BEST |
| deep_15_25 | 65% | +67% | 12.8% | 6.4% | Good |
| value_20_30 | 70% | +50% | 10.0% | 5.0% | Okay |
| value_20_25 | 75% | +25% | **-25%** | N/A | ❌ SKIP |
| mid_40_50 | 80% | +25% | **0%** | N/A | ❌ SKIP |

**Critical Insight:** Strategies with negative or zero Kelly should NOT be traded!

### Recommended Configuration (Balanced)

```yaml
position_sizing:
  method: "fractional_kelly"
  kelly_fraction: 0.50          # Half Kelly (reduces volatility)
  max_bet_percentage: 15        # Never bet more than 15%
  min_bet_percentage: 3         # Always bet at least 3%

vault:
  enabled: true
  deposit_rate: 0.20            # Save 20% of every profit
  emergency_withdrawal: true    # Can tap vault if critical

risk_limits:
  max_drawdown_percentage: 25   # Stop trading if down 25%
  max_daily_loss_percentage: 12 # Stop for day if down 12%
  max_consecutive_losses: 5     # Pause after 5 losses in a row
```

### The Vault System

Automatically protect profits by moving a portion to a "vault" that's never risked:

```
WIN $20 profit:
├── $16 → Bankroll (compounds, can be lost)
└── $4  → Vault (protected FOREVER)

LOSE $15:
├── Comes entirely from bankroll
└── Vault remains untouched ($4 safe)
```

### Bet Sizing by Drawdown

Automatically reduce risk during losing periods:

| Current Drawdown | Bet Size Multiplier | Example (10% base) |
|------------------|---------------------|---------------------|
| 0-5% | 100% | 10% |
| 5-10% | 80% | 8% |
| 10-20% | 60% | 6% |
| 20-30% | 40% | 4% |
| 30-40% | 20% | 2% |
| 40%+ | 0% | **STOP TRADING** |

### Quick Bet Size Reference

| Strategy | Recommended Bet | Max Bet |
|----------|-----------------|---------|
| ultra_05_15 | 8-10% | 12% |
| ultra_05_10 | 5-7% | 10% |
| deep_10_20 | 10-12% | 15% |
| deep_10_25 | 12-15% | 18% |
| deep_15_25 | 6-8% | 10% |
| value_20_30 | 5-7% | 10% |
| mid_35_50 | 3-5% | 7% |

---

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| **Entry Price** | The price at which we buy (e.g., 20%) |
| **Exit Price** | The price at which we sell (e.g., 25%) |
| **Win Rate** | Percentage of trades that hit the exit target |
| **Break-Even WR** | Win rate needed to not lose money |
| **Resolution** | When the 15-minute market ends and settles |
| **Bounce** | When price moves back toward 50% from an extreme |
| **Deep Value** | Strategies with very low entry prices (10-20%) |
| **Fade** | Betting against the current favorite |
| **Paper Trade** | Simulated trade with no real money |
| **Champion** | The best-performing strategy |

### Formulas

**Profit on Win:**
```
profit_pct = (exit_price - entry_price) / entry_price × 100
```

**Break-Even Win Rate:**
```
break_even_wr = loss_size / (win_size + loss_size)

Example (20% → 25%):
  win_size = 25%
  loss_size = 100% (entry goes to 0)
  break_even = 100 / (25 + 100) = 80%
```

**Expected Value per Trade:**
```
ev = (win_rate × avg_win) - ((1 - win_rate) × avg_loss)
```

**Kelly Criterion (Position Sizing):**
```
kelly_fraction = (win_rate × (1 + win_loss_ratio) - 1) / win_loss_ratio
```

### References

- [Polymarket API Documentation](https://docs.polymarket.com/)
- [Polymarket CLOB Client (Python)](https://github.com/Polymarket/py-clob-client)
- [OpenRouter API](https://openrouter.ai/docs)

---

*Document Version: 1.0*
*Last Updated: January 2025*
*Author: Polymarket Quant Trading System*
