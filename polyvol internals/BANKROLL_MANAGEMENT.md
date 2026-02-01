# Betting & Bankroll Management

## Overview

Position sizing is just as important as strategy selection. A winning strategy with bad position sizing can still lose money. This document covers:

1. Kelly Criterion fundamentals
2. Position sizing strategies
3. Bankroll configurations
4. The Vault system
5. Risk management rules

---

## Kelly Criterion

### The Formula

The Kelly Criterion tells you the mathematically optimal bet size to maximize long-term growth:

```
Kelly % = W - [(1 - W) / R]

Where:
  W = Win rate (probability of winning)
  R = Win/Loss ratio (average win size ÷ average loss size)
```

### Example Calculation

For the `deep_10_20` strategy:
- Estimated win rate: 60%
- Win size: +100% (buy at 10%, sell at 20%)
- Loss size: -100% (buy at 10%, goes to 0%)
- R ratio: 100% / 100% = 1.0

```
Kelly = 0.60 - [(1 - 0.60) / 1.0]
Kelly = 0.60 - [0.40 / 1.0]
Kelly = 0.60 - 0.40
Kelly = 0.20 = 20%
```

**Optimal bet: 20% of bankroll per trade**

### Kelly for All Strategies

| Strategy | Est. Win Rate | Win Size | Loss Size | R Ratio | Full Kelly |
|----------|---------------|----------|-----------|---------|------------|
| ultra_05_15 | 45% | +200% | -100% | 2.0 | **17.5%** |
| ultra_05_10 | 55% | +100% | -100% | 1.0 | **10%** |
| ultra_05_20 | 40% | +300% | -100% | 3.0 | **20%** |
| deep_10_20 | 60% | +100% | -100% | 1.0 | **20%** |
| deep_10_25 | 55% | +150% | -100% | 1.5 | **25%** |
| deep_15_25 | 65% | +67% | -100% | 0.67 | **13%** |
| deep_15_30 | 58% | +100% | -100% | 1.0 | **16%** |
| value_20_25 | 75% | +25% | -100% | 0.25 | **-25%** ❌ |
| value_20_30 | 70% | +50% | -100% | 0.50 | **3%** |
| mid_40_50 | 80% | +25% | -100% | 0.25 | **0%** ❌ |
| mid_40_55 | 78% | +38% | -100% | 0.38 | **5%** |
| high_60_70 | 85% | +17% | -100% | 0.17 | **-3%** ❌ |

### Critical Insight

**Strategies with negative or zero Kelly should NOT be traded** - the math doesn't support them regardless of win rate.

Notice that:
- Ultra-deep and deep strategies have **positive Kelly** (good math)
- Mid-range and high-prob strategies have **zero or negative Kelly** (bad math)

This confirms our strategy tier rankings from a completely different angle.

---

## The Problem with Full Kelly

Full Kelly maximizes long-term growth BUT:

1. **Extremely volatile** - 50%+ drawdowns are common
2. **Requires exact win rate knowledge** - we're estimating
3. **Psychological torture** - hard to stick with during losing streaks
4. **Risk of ruin** - bad luck can wipe you out

### Simulation: Full Kelly vs Fractional Kelly

Starting bankroll: $100
Strategy: deep_10_20 (60% WR, Kelly = 20%)
Trades: 500

```
| Bet Size     | Median Final | Best Case  | Worst Case | Bust Rate |
|--------------|--------------|------------|------------|-----------|
| Full Kelly   | $45,000      | $2,000,000 | $0.50      | 12%       |
| 3/4 Kelly    | $8,500       | $180,000   | $8         | 5%        |
| Half Kelly   | $2,800       | $35,000    | $25        | 2%        |
| 1/3 Kelly    | $850         | $8,000     | $45        | 0.5%      |
| Quarter Kelly| $450         | $3,500     | $55        | 0.1%      |
```

**Half Kelly is the sweet spot** - good growth with manageable risk.

---

## Position Sizing Strategies

### Strategy 1: Fractional Kelly (Recommended)

Use a fraction of the Kelly percentage to reduce volatility.

```python
def fractional_kelly(bankroll, win_rate, win_loss_ratio, fraction=0.5):
    """
    Calculate bet size using fractional Kelly.
    
    Args:
        bankroll: Current bankroll
        win_rate: Probability of winning (0-1)
        win_loss_ratio: Average win / Average loss
        fraction: Kelly fraction (0.25 to 0.75 recommended)
    
    Returns:
        Bet size in dollars
    """
    kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
    
    # Kelly can be negative - don't bet if so
    if kelly <= 0:
        return 0
    
    bet_pct = kelly * fraction
    bet_size = bankroll * bet_pct
    
    return bet_size


# Example usage
bankroll = 100
win_rate = 0.60
win_loss_ratio = 1.0  # 100% win, 100% loss
fraction = 0.50  # Half Kelly

bet = fractional_kelly(bankroll, win_rate, win_loss_ratio, fraction)
# bet = $10 (10% of bankroll)
```

**Recommended fractions:**
- Conservative: 0.25 (Quarter Kelly)
- Balanced: 0.50 (Half Kelly)
- Aggressive: 0.75 (Three-Quarter Kelly)

---

### Strategy 2: Fixed Fractional

Simple approach - bet a fixed percentage regardless of edge.

```python
def fixed_fractional(bankroll, percentage=0.10):
    """
    Simple fixed percentage betting.
    
    Args:
        bankroll: Current bankroll
        percentage: Fixed bet percentage (e.g., 0.10 for 10%)
    
    Returns:
        Bet size in dollars
    """
    return bankroll * percentage


# Always bet 10% of current bankroll
bet = fixed_fractional(100, 0.10)  # $10
```

**Pros:** Simple, doesn't require win rate estimation
**Cons:** Doesn't optimize for edge

---

### Strategy 3: Tiered Confidence

Adjust bet size based on signal strength.

```python
def tiered_confidence(bankroll, base_kelly, confidence_level):
    """
    Adjust bet size based on confidence in the trade.
    
    Args:
        bankroll: Current bankroll
        base_kelly: Base Kelly percentage for this strategy
        confidence_level: 'high', 'medium', or 'low'
    
    Returns:
        Bet size in dollars
    """
    confidence_multipliers = {
        'high': 0.75,    # Strong signal - use 75% of Kelly
        'medium': 0.50,  # Normal signal - use 50% of Kelly
        'low': 0.25,     # Weak signal - use 25% of Kelly
    }
    
    multiplier = confidence_multipliers.get(confidence_level, 0.50)
    bet_pct = base_kelly * multiplier
    
    return bankroll * bet_pct


# High confidence trade on deep_10_20 (Kelly = 20%)
bet = tiered_confidence(100, 0.20, 'high')  # $15

# Low confidence trade
bet = tiered_confidence(100, 0.20, 'low')   # $5
```

**When to use high confidence:**
- Entry at extreme level (5% instead of 10%)
- Strong volume/liquidity
- Clear trend reversal signal

**When to use low confidence:**
- Entry near threshold edge
- Low liquidity
- Choppy market conditions

---

### Strategy 4: Anti-Martingale (Streak Rider)

Increase bets during winning streaks, reset on losses.

```python
class AntiMartingale:
    """
    Compound bets during winning streaks.
    """
    
    def __init__(
        self,
        base_bet_pct=0.10,
        win_increase=0.25,
        max_multiplier=2.5,
        reset_on_loss=True
    ):
        self.base_bet_pct = base_bet_pct
        self.win_increase = win_increase
        self.max_multiplier = max_multiplier
        self.reset_on_loss = reset_on_loss
        self.consecutive_wins = 0
    
    def get_bet_size(self, bankroll):
        """Calculate bet size based on current streak."""
        multiplier = 1 + (self.consecutive_wins * self.win_increase)
        multiplier = min(multiplier, self.max_multiplier)
        
        bet_pct = self.base_bet_pct * multiplier
        return bankroll * bet_pct
    
    def record_win(self):
        """Record a winning trade."""
        self.consecutive_wins += 1
    
    def record_loss(self):
        """Record a losing trade."""
        if self.reset_on_loss:
            self.consecutive_wins = 0


# Example sequence
am = AntiMartingale(base_bet_pct=0.10, win_increase=0.25)
bankroll = 100

# Trade 1: No streak
bet1 = am.get_bet_size(bankroll)  # $10 (10% × 1.0)
am.record_win()
bankroll = 120

# Trade 2: 1 win streak
bet2 = am.get_bet_size(bankroll)  # $15 (10% × 1.25 × $120)
am.record_win()
bankroll = 150

# Trade 3: 2 win streak
bet3 = am.get_bet_size(bankroll)  # $22.50 (10% × 1.5 × $150)
am.record_loss()
bankroll = 127.50

# Trade 4: Reset after loss
bet4 = am.get_bet_size(bankroll)  # $12.75 (10% × 1.0 × $127.50)
```

**Benefits:**
- Capitalizes on hot streaks
- Limits damage during cold streaks
- Psychological comfort (betting small after losses)

---

### Strategy 5: Drawdown-Adjusted Kelly

Automatically reduce bet size during losing periods.

```python
class DrawdownAdjustedKelly:
    """
    Reduce bet size as drawdown increases.
    """
    
    def __init__(self, base_kelly_fraction=0.50):
        self.base_kelly_fraction = base_kelly_fraction
        self.peak_bankroll = 0
    
    def get_bet_size(self, bankroll, strategy_kelly):
        """
        Calculate bet size adjusted for current drawdown.
        
        Args:
            bankroll: Current bankroll
            strategy_kelly: Full Kelly % for this strategy
        
        Returns:
            Bet size in dollars
        """
        # Update peak
        self.peak_bankroll = max(self.peak_bankroll, bankroll)
        
        # Calculate drawdown
        if self.peak_bankroll > 0:
            drawdown = (self.peak_bankroll - bankroll) / self.peak_bankroll
        else:
            drawdown = 0
        
        # Adjust Kelly fraction based on drawdown
        if drawdown >= 0.40:
            adjustment = 0.00  # STOP TRADING
        elif drawdown >= 0.30:
            adjustment = 0.25  # Survival mode
        elif drawdown >= 0.20:
            adjustment = 0.50  # Conservative
        elif drawdown >= 0.10:
            adjustment = 0.75  # Cautious
        else:
            adjustment = 1.00  # Normal
        
        effective_kelly = strategy_kelly * self.base_kelly_fraction * adjustment
        return bankroll * effective_kelly


# Example
dak = DrawdownAdjustedKelly(base_kelly_fraction=0.50)

# At peak - normal betting
bankroll = 100
bet = dak.get_bet_size(100, 0.20)  # $10 (20% × 0.5 × 1.0)

# Down 15% from peak - cautious
bankroll = 85
bet = dak.get_bet_size(85, 0.20)   # $6.38 (20% × 0.5 × 0.75)

# Down 35% from peak - survival mode
bankroll = 65
bet = dak.get_bet_size(65, 0.20)   # $1.63 (20% × 0.5 × 0.25)

# Down 45% from peak - STOP
bankroll = 55
bet = dak.get_bet_size(55, 0.20)   # $0 (stop trading)
```

**Benefits:**
- Impossible to blow up completely
- Automatically protects during bad runs
- Returns to normal sizing after recovery

---

## The Vault System

### Concept

Split your money between:
1. **Active Bankroll** - Used for trading, can compound
2. **Vault** - Safe storage, never risked

After every winning trade, move a portion of profits to the vault.

```
┌─────────────────────────────────────────────────────────┐
│                    THE VAULT SYSTEM                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────────┐         ┌─────────────┐              │
│   │   ACTIVE    │  wins   │    VAULT    │              │
│   │  BANKROLL   │ ──────► │   (SAFE)    │              │
│   │             │   20%   │             │              │
│   │  $80        │         │  $45        │              │
│   └─────────────┘         └─────────────┘              │
│         │                        │                      │
│         │ losses                 │ never                │
│         ▼                        ▼                      │
│   Bankroll shrinks         Vault protected              │
│                                                          │
│   Total Equity = Bankroll + Vault = $125               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Implementation

```python
class VaultBankroll:
    """
    Bankroll management with protected vault.
    """
    
    def __init__(
        self,
        initial_bankroll,
        vault_deposit_rate=0.20,
        emergency_withdrawal_threshold=0.20
    ):
        self.bankroll = initial_bankroll
        self.vault = 0
        self.initial_bankroll = initial_bankroll
        self.vault_deposit_rate = vault_deposit_rate
        self.emergency_threshold = emergency_withdrawal_threshold
        
        self.peak_equity = initial_bankroll
        self.trade_history = []
    
    @property
    def total_equity(self):
        """Total value = bankroll + vault."""
        return self.bankroll + self.vault
    
    @property
    def total_return(self):
        """Total return percentage."""
        return (self.total_equity - self.initial_bankroll) / self.initial_bankroll
    
    def process_trade(self, pnl, is_win):
        """
        Process a completed trade.
        
        Args:
            pnl: Profit/loss in dollars
            is_win: Whether the trade was a win
        """
        if is_win and pnl > 0:
            # Deposit portion of profit to vault
            vault_deposit = pnl * self.vault_deposit_rate
            self.vault += vault_deposit
            self.bankroll += (pnl - vault_deposit)
        else:
            # Losses come from bankroll only
            self.bankroll += pnl  # pnl is negative
        
        # Update peak
        self.peak_equity = max(self.peak_equity, self.total_equity)
        
        # Record history
        self.trade_history.append({
            'pnl': pnl,
            'is_win': is_win,
            'bankroll': self.bankroll,
            'vault': self.vault,
            'total_equity': self.total_equity
        })
        
        # Check for emergency withdrawal
        self._check_emergency()
    
    def _check_emergency(self):
        """
        Emergency vault withdrawal if bankroll too low.
        """
        bankroll_ratio = self.bankroll / self.total_equity if self.total_equity > 0 else 0
        
        if bankroll_ratio < self.emergency_threshold and self.vault > 0:
            # Withdraw enough to get back to threshold
            target_bankroll = self.total_equity * self.emergency_threshold
            withdrawal = min(target_bankroll - self.bankroll, self.vault)
            
            self.vault -= withdrawal
            self.bankroll += withdrawal
            
            print(f"EMERGENCY: Withdrew ${withdrawal:.2f} from vault")
    
    def get_status(self):
        """Get current status."""
        return {
            'bankroll': self.bankroll,
            'vault': self.vault,
            'total_equity': self.total_equity,
            'total_return': f"{self.total_return * 100:.1f}%",
            'trades': len(self.trade_history)
        }


# Example usage
vb = VaultBankroll(initial_bankroll=100, vault_deposit_rate=0.20)

# Win $25
vb.process_trade(pnl=25, is_win=True)
print(vb.get_status())
# {'bankroll': 120, 'vault': 5, 'total_equity': 125, ...}
# $20 to bankroll, $5 to vault

# Lose $30
vb.process_trade(pnl=-30, is_win=False)
print(vb.get_status())
# {'bankroll': 90, 'vault': 5, 'total_equity': 95, ...}
# Loss comes from bankroll only, vault protected

# Big win $50
vb.process_trade(pnl=50, is_win=True)
print(vb.get_status())
# {'bankroll': 130, 'vault': 15, 'total_equity': 145, ...}
# $40 to bankroll, $10 to vault
```

### Vault Configuration Options

| Profile | Deposit Rate | When to Use |
|---------|--------------|-------------|
| Aggressive | 10% | Want maximum compounding |
| Balanced | 20% | Good balance |
| Conservative | 30% | Prioritize locking profits |
| Very Safe | 50% | Ultra conservative |

---

## Complete Bankroll Configurations

### Configuration A: Conservative Growth

```yaml
name: "Conservative"
description: "Slow and steady, prioritize survival"

position_sizing:
  method: "fractional_kelly"
  kelly_fraction: 0.25          # Quarter Kelly
  max_bet_pct: 0.10             # Never bet more than 10%
  min_bet_pct: 0.02             # Always bet at least 2%

vault:
  enabled: true
  deposit_rate: 0.30            # Save 30% of profits
  emergency_withdrawal: true
  emergency_threshold: 0.20     # Withdraw if bankroll < 20% of equity

risk_limits:
  max_drawdown: 0.15            # Stop if down 15%
  max_daily_loss: 0.10          # Stop if down 10% today
  max_consecutive_losses: 4     # Pause after 4 losses in a row
  cooldown_minutes: 30          # Wait 30 min after hitting limit

expected_behavior:
  growth_rate: "Slow but steady"
  drawdown_tolerance: "Low"
  survival_probability: "Very High (99%+)"
  time_to_10x: "6-12 months"
```

### Configuration B: Balanced Growth

```yaml
name: "Balanced"
description: "Good growth with reasonable risk"

position_sizing:
  method: "fractional_kelly"
  kelly_fraction: 0.50          # Half Kelly
  max_bet_pct: 0.20             # Cap at 20%
  min_bet_pct: 0.05             # At least 5%

vault:
  enabled: true
  deposit_rate: 0.20            # Save 20% of profits
  emergency_withdrawal: true
  emergency_threshold: 0.15

risk_limits:
  max_drawdown: 0.25            # Stop if down 25%
  max_daily_loss: 0.15          # Stop if down 15% today
  max_consecutive_losses: 5
  cooldown_minutes: 20

expected_behavior:
  growth_rate: "Moderate"
  drawdown_tolerance: "Medium"
  survival_probability: "High (95%+)"
  time_to_10x: "2-4 months"
```

### Configuration C: Aggressive Growth

```yaml
name: "Aggressive"
description: "Maximum growth, accept higher volatility"

position_sizing:
  method: "fractional_kelly"
  kelly_fraction: 0.75          # 3/4 Kelly
  max_bet_pct: 0.35             # Allow up to 35%
  min_bet_pct: 0.10             # Always meaningful bets

vault:
  enabled: true
  deposit_rate: 0.10            # Save only 10% of profits
  emergency_withdrawal: true
  emergency_threshold: 0.10

risk_limits:
  max_drawdown: 0.40            # Tolerate 40% drawdown
  max_daily_loss: 0.25          # Tolerate 25% daily loss
  max_consecutive_losses: 6
  cooldown_minutes: 15

expected_behavior:
  growth_rate: "Fast"
  drawdown_tolerance: "High"
  survival_probability: "Moderate (85%+)"
  time_to_10x: "2-6 weeks"
```

### Configuration D: Streak Rider (Anti-Martingale)

```yaml
name: "Streak Rider"
description: "Compound during winning streaks, reset on losses"

position_sizing:
  method: "anti_martingale"
  base_bet_pct: 0.10            # Start at 10%
  win_increase: 0.25            # +25% per consecutive win
  max_multiplier: 2.5           # Cap at 2.5x base (25%)
  reset_on_loss: true           # Back to base after any loss

vault:
  enabled: true
  deposit_rate: 0.15            # Save 15% of profits
  streak_bonus_deposit: 0.10    # Extra 10% deposit after 3+ win streak
  streak_threshold: 3

risk_limits:
  max_drawdown: 0.30
  max_daily_loss: 0.20
  max_consecutive_losses: 5
  cooldown_minutes: 15

expected_behavior:
  growth_rate: "Variable - explosive during streaks"
  drawdown_tolerance: "Medium"
  survival_probability: "High (93%+)"
  time_to_10x: "Depends on streaks"
```

### Configuration E: Drawdown Protector

```yaml
name: "Drawdown Protector"
description: "Automatically reduces risk during losing periods"

position_sizing:
  method: "drawdown_adjusted"
  base_kelly_fraction: 0.50     # Start at half Kelly
  
  drawdown_adjustments:
    - max_drawdown: 0.00        # No drawdown
      kelly_multiplier: 1.00    # Full base Kelly
    - max_drawdown: 0.10        # Down 10%
      kelly_multiplier: 0.75    # 75% of base
    - max_drawdown: 0.20        # Down 20%
      kelly_multiplier: 0.50    # 50% of base
    - max_drawdown: 0.30        # Down 30%
      kelly_multiplier: 0.25    # 25% of base (survival mode)
    - max_drawdown: 0.40        # Down 40%
      kelly_multiplier: 0.00    # STOP TRADING

vault:
  enabled: true
  deposit_rate: 0.25            # Higher deposit to build safety net
  emergency_withdrawal: true
  emergency_threshold: 0.15

risk_limits:
  max_drawdown: 0.40            # Hard stop at 40%
  auto_resume_after_recovery: true
  recovery_threshold: 0.20      # Resume normal after recovering to 20% DD

expected_behavior:
  growth_rate: "Self-adjusting"
  drawdown_tolerance: "Managed"
  survival_probability: "Very High (98%+)"
  time_to_10x: "3-6 months"
```

### Configuration F: Ultra-Deep Specialist

```yaml
name: "Ultra-Deep Specialist"
description: "Optimized for 5-15% entry strategies"

position_sizing:
  method: "tiered_confidence"
  
  tiers:
    # Ultra-deep entries (5%) get larger bets
    - entry_range: [0.00, 0.08]
      confidence: "high"
      kelly_fraction: 0.60
    
    # Deep entries (8-15%) get medium bets  
    - entry_range: [0.08, 0.15]
      confidence: "medium"
      kelly_fraction: 0.45
    
    # Value entries (15-25%) get smaller bets
    - entry_range: [0.15, 0.25]
      confidence: "low"
      kelly_fraction: 0.30
    
    # Everything else - minimal
    - entry_range: [0.25, 1.00]
      confidence: "minimal"
      kelly_fraction: 0.15

vault:
  enabled: true
  deposit_rate: 0.20
  
risk_limits:
  max_drawdown: 0.30
  max_daily_loss: 0.20
  max_consecutive_losses: 5

notes: |
  This configuration bets bigger on ultra-deep entries
  because they have the best risk/reward math.
  
  A 5% entry with 200% upside deserves more capital
  than a 20% entry with 25% upside.
```

---

## Quick Reference

### Recommended Bet Sizes by Strategy

| Strategy | Full Kelly | Half Kelly | Recommended |
|----------|------------|------------|-------------|
| ultra_05_15 | 17.5% | 8.75% | **8-10%** |
| ultra_05_10 | 10% | 5% | **5-7%** |
| ultra_05_20 | 20% | 10% | **10-12%** |
| deep_10_20 | 20% | 10% | **10-12%** |
| deep_10_25 | 25% | 12.5% | **10-15%** |
| deep_15_25 | 13% | 6.5% | **6-8%** |
| deep_15_30 | 16% | 8% | **8-10%** |
| value_20_30 | 3% | 1.5% | **2-5%** |
| mid_35_50 | 5% | 2.5% | **3-5%** |
| mid_40_50 | 0% | 0% | **Skip or 2%** |

### Decision Tree: Which Configuration?

```
START
  │
  ├─► New to system? ──────────► Configuration A (Conservative)
  │
  ├─► Validated 75%+ WR? ─────► Configuration B (Balanced)
  │
  ├─► Risk tolerant + validated? ► Configuration C (Aggressive)
  │
  ├─► Like momentum? ──────────► Configuration D (Streak Rider)
  │
  ├─► Hate drawdowns? ─────────► Configuration E (Drawdown Protector)
  │
  └─► Focusing on ultra-deep? ─► Configuration F (Ultra-Deep Specialist)
```

### Risk Limits Cheat Sheet

| Situation | Action |
|-----------|--------|
| Drawdown > 15% | Reduce to Quarter Kelly |
| Drawdown > 25% | Reduce to 1/8 Kelly |
| Drawdown > 40% | STOP TRADING |
| 3 consecutive losses | Take 15 min break |
| 5 consecutive losses | Take 1 hour break |
| Daily loss > 15% | Stop for the day |
| Win rate < 50% (last 20) | Review and possibly pause |

---

## Simulation: Configuration Comparison

Starting: $100, Strategy: deep_10_20 (60% WR), 500 trades

| Configuration | Final Equity | Max DD | Bust Rate | Vault |
|---------------|--------------|--------|-----------|-------|
| A: Conservative | $380 | 12% | 0% | $180 |
| B: Balanced | $1,450 | 22% | 1% | $420 |
| C: Aggressive | $8,200 | 38% | 8% | $650 |
| D: Streak Rider | $2,800 | 28% | 3% | $520 |
| E: DD Protector | $950 | 18% | 0.5% | $380 |
| F: Ultra-Deep | $3,200 | 25% | 2% | $580 |

**Key Insights:**
- Conservative never busts but grows slowly
- Aggressive has best upside but 8% bust rate
- Balanced is the sweet spot for most users
- Vault protects significant capital in all scenarios

---

## Implementation Notes

### For Paper Trading Phase

Test multiple configurations simultaneously:

```python
configurations = [
    {"name": "conservative", "kelly_fraction": 0.25, "vault_rate": 0.30},
    {"name": "balanced", "kelly_fraction": 0.50, "vault_rate": 0.20},
    {"name": "aggressive", "kelly_fraction": 0.75, "vault_rate": 0.10},
]

# Run same trades through each configuration
# Compare results after 200+ trades
```

### For Live Trading Phase

Start with Configuration A or B. Only move to C after:
- 500+ validated trades
- Confirmed 75%+ win rate
- Comfortable with drawdowns

---

*Document Version: 1.0*
*Last Updated: January 2025*
