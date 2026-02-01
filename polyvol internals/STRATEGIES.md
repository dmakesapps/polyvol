# Strategy Documentation

## Complete Strategy Reference

This document contains detailed specifications for every strategy we run.

---

## Understanding the Math

### The Resolution Reality

Every Polymarket 15-minute crypto market ends with:
- **Winner side**: 100%
- **Loser side**: 0%

There is NO middle ground. This is critical for understanding our risk.

### Profit and Loss Calculation

When you buy at price P and sell at price S:

```
Profit % = ((S - P) / P) × 100

Examples:
  Buy at 10%, sell at 20%: ((0.20 - 0.10) / 0.10) × 100 = +100%
  Buy at 20%, sell at 25%: ((0.25 - 0.20) / 0.20) × 100 = +25%
  Buy at 40%, sell at 50%: ((0.50 - 0.40) / 0.40) × 100 = +25%
  Buy at 10%, goes to 0%:  ((0.00 - 0.10) / 0.10) × 100 = -100%
```

### Break-Even Win Rate

The win rate needed to not lose money:

```
Break-Even WR = |Loss %| / (|Loss %| + |Gain %|)

Examples:
  10% → 20% (+100% gain, -100% loss): 100 / (100 + 100) = 50%
  10% → 25% (+150% gain, -100% loss): 100 / (100 + 150) = 40%
  20% → 25% (+25% gain, -100% loss):  100 / (100 + 25) = 80%
  40% → 50% (+25% gain, -100% loss):  100 / (100 + 25) = 80%
```

### Key Insight

**The lower your entry price, the more forgiving the math.**

| Entry | Exit | Profit if Win | Break-Even WR | Forgiveness |
|-------|------|---------------|---------------|-------------|
| 5% | 15% | +200% | 33% | Very forgiving |
| 10% | 20% | +100% | 50% | Forgiving |
| 10% | 25% | +150% | 40% | Very forgiving |
| 15% | 25% | +67% | 60% | Moderate |
| 20% | 25% | +25% | 80% | Unforgiving |
| 40% | 50% | +25% | 80% | Unforgiving |
| 80% | 90% | +12.5% | 89% | Extremely unforgiving |

---

## Strategy Tiers

### Critical Insight: Resolution Volatility

**As the 15-minute market approaches resolution, price movements become EXTREME.**

```
TIME REMAINING    TYPICAL BEHAVIOR
─────────────────────────────────────────────────────────
10-15 min left    Prices oscillate, mean reversion works
5-10 min left     Volatility increases, trends emerge  
2-5 min left      EXTREME moves as traders panic/FOMO
0-2 min left      Price rushes toward 0% or 100%
```

**Why this happens:**
1. Traders who are wrong start panic-selling
2. Traders who are right pile in for the kill
3. The market KNOWS it's about to resolve to 0 or 100
4. No time for mean reversion - it's a one-way trip

**Strategic implications:**
- Early entries (10+ min left): Mean reversion strategies work
- Late entries (< 5 min left): Momentum/trend strategies may work better
- Ultra-deep entries (5-10%): Often happen in final minutes as one side collapses

---

### Tier 1: Deep Value

**Entry range: 5% - 20%**
**Break-even win rate: 25% - 67%**
**Recommendation: PRIMARY FOCUS**

These strategies buy when one side is heavily discounted. The math strongly favors us because we only need 25-60% win rate to profit.

#### ultra_05_10 ⭐ SUPER STRATEGY
```yaml
id: ultra_05_10
name: "Ultra Deep 5→10"
tier: 1

parameters:
  entry_threshold: 0.05
  exit_threshold: 0.10
  stop_loss: null

math:
  profit_if_win: +100%
  loss_if_lose: -100%
  break_even_wr: 50%

notes: |
  SUPER STRATEGY - Extreme deep value
  Entry at 5% means market thinks this side is nearly dead.
  Only need 50% win rate to profit.
  
  KEY INSIGHT: 5% entries often happen in final 2-5 minutes
  when one side is collapsing. But sometimes the "dead" side
  makes a miraculous comeback if BTC reverses sharply.
  
  Risk: Very rare entries, may be "dead money" that never bounces.
  Reward: When it bounces, even a small move to 10% = 100% profit.

expected_frequency: Extremely rare (< 2% of markets)
expected_win_rate: 45-60%
confidence: Medium
special_note: Often triggers during resolution volatility phase
```

#### ultra_05_15 ⭐ SUPER STRATEGY
```yaml
id: ultra_05_15
name: "Ultra Deep 5→15"
tier: 1

parameters:
  entry_threshold: 0.05
  exit_threshold: 0.15
  stop_loss: null

math:
  profit_if_win: +200%
  loss_if_lose: -100%
  break_even_wr: 33%

notes: |
  SUPER STRATEGY - Best risk/reward in entire portfolio
  Only need 33% win rate to profit. This is VERY forgiving.
  
  If price is at 5%, the market is saying "95% chance this side loses."
  But markets overshoot. If it bounces to just 15%, you TRIPLE your money.
  
  Even if you're wrong 2 out of 3 times:
  - 2 losses × -100% = -200%
  - 1 win × +200% = +200%
  - Net: Break even at 33% WR, profit above that
  
  This is the mathematical sweet spot.

expected_frequency: Extremely rare (< 2% of markets)
expected_win_rate: 40-55%
confidence: High (math is very favorable)
special_note: Target this when you see resolution panic selling
```

#### ultra_05_20
```yaml
id: ultra_05_20
name: "Ultra Deep 5→20"
tier: 1

parameters:
  entry_threshold: 0.05
  exit_threshold: 0.20
  stop_loss: null

math:
  profit_if_win: +300%
  loss_if_lose: -100%
  break_even_wr: 25%

notes: |
  Aggressive target but incredible math.
  Only need 25% win rate - be right 1 in 4 times.
  
  This is essentially buying lottery tickets with positive expected value.
  Most will lose, but winners pay 4:1.

expected_frequency: Extremely rare (< 2% of markets)
expected_win_rate: 30-45%
confidence: Medium
```

#### deep_05_15
```yaml
id: deep_05_15
name: "Deep Value 5→15"
tier: 1

parameters:
  entry_threshold: 0.05
  exit_threshold: 0.15
  stop_loss: null

math:
  profit_if_win: +200%
  loss_if_lose: -100%
  break_even_wr: 33%

notes: |
  Same as ultra_05_15 (kept for naming consistency).
  Extremely rare entry. Price must drop to 5%.
  When it hits, we have huge edge - only need 33% WR.
  May go days without a trade.
  
expected_frequency: Very rare (< 5% of markets)
expected_win_rate: 50-70%
confidence: Medium
```

#### deep_10_15
```yaml
id: deep_10_15
name: "Deep Value 10→15"
tier: 1

parameters:
  entry_threshold: 0.10
  exit_threshold: 0.15
  stop_loss: null

math:
  profit_if_win: +50%
  loss_if_lose: -100%
  break_even_wr: 67%

notes: |
  Rare entry with small bounce target.
  Need 67% WR which is achievable.
  Quick exits expected.

expected_frequency: Rare (5-10% of markets)
expected_win_rate: 65-80%
confidence: Medium
```

#### deep_10_20 ⭐ RECOMMENDED
```yaml
id: deep_10_20
name: "Deep Value 10→20"
tier: 1

parameters:
  entry_threshold: 0.10
  exit_threshold: 0.20
  stop_loss: null

math:
  profit_if_win: +100%
  loss_if_lose: -100%
  break_even_wr: 50%

notes: |
  RECOMMENDED STRATEGY
  Rare entry but excellent math.
  Only need to be right 50% of the time.
  When price is at 10%, often means oversold.

expected_frequency: Rare (5-10% of markets)
expected_win_rate: 55-70%
confidence: High
```

#### deep_10_25 ⭐ RECOMMENDED
```yaml
id: deep_10_25
name: "Deep Value 10→25"
tier: 1

parameters:
  entry_threshold: 0.10
  exit_threshold: 0.25
  stop_loss: null

math:
  profit_if_win: +150%
  loss_if_lose: -100%
  break_even_wr: 40%

notes: |
  RECOMMENDED STRATEGY
  Best risk/reward ratio in our portfolio.
  Only need 40% win rate to profit.
  Let winners run further.

expected_frequency: Rare (5-10% of markets)
expected_win_rate: 50-65%
confidence: High
```

#### deep_10_30
```yaml
id: deep_10_30
name: "Deep Value 10→30"
tier: 1

parameters:
  entry_threshold: 0.10
  exit_threshold: 0.30
  stop_loss: null

math:
  profit_if_win: +200%
  loss_if_lose: -100%
  break_even_wr: 33%

notes: |
  Aggressive target but excellent math.
  If 10% bounces to 30% even 35% of time, we profit.
  May miss some trades that only bounce to 20-25%.

expected_frequency: Rare (5-10% of markets)
expected_win_rate: 40-55%
confidence: Medium
```

#### deep_15_20
```yaml
id: deep_15_20
name: "Deep Value 15→20"
tier: 1

parameters:
  entry_threshold: 0.15
  exit_threshold: 0.20
  stop_loss: null

math:
  profit_if_win: +33%
  loss_if_lose: -100%
  break_even_wr: 75%

notes: |
  Moderate entry, tight target.
  Need 75% WR which is our goal anyway.
  Quick scalp opportunity.

expected_frequency: Uncommon (10-15% of markets)
expected_win_rate: 70-85%
confidence: Medium
```

#### deep_15_25 ⭐ RECOMMENDED
```yaml
id: deep_15_25
name: "Deep Value 15→25"
tier: 1

parameters:
  entry_threshold: 0.15
  exit_threshold: 0.25
  stop_loss: null

math:
  profit_if_win: +67%
  loss_if_lose: -100%
  break_even_wr: 60%

notes: |
  RECOMMENDED STRATEGY
  Good balance of frequency and math.
  60% break-even is very achievable.
  Enough room for price to bounce.

expected_frequency: Uncommon (10-15% of markets)
expected_win_rate: 60-75%
confidence: High
```

#### deep_15_30
```yaml
id: deep_15_30
name: "Deep Value 15→30"
tier: 1

parameters:
  entry_threshold: 0.15
  exit_threshold: 0.30
  stop_loss: null

math:
  profit_if_win: +100%
  loss_if_lose: -100%
  break_even_wr: 50%

notes: |
  Solid entry with good target.
  Only need 50% WR.
  Lets winners run.

expected_frequency: Uncommon (10-15% of markets)
expected_win_rate: 50-65%
confidence: Medium
```

---

### Tier 2: Value

**Entry range: 20% - 35%**
**Break-even win rate: 60% - 80%**
**Recommendation: TEST TO VALIDATE**

These strategies are more common but require higher win rates.

#### value_20_25
```yaml
id: value_20_25
name: "Value 20→25"
tier: 2

parameters:
  entry_threshold: 0.20
  exit_threshold: 0.25
  stop_loss: null

math:
  profit_if_win: +25%
  loss_if_lose: -100%
  break_even_wr: 80%

notes: |
  ORIGINAL STRATEGY - USE AS BASELINE
  Need 80% win rate - this is HARD.
  Small profit, full loss potential.
  Keep as control to compare others against.

expected_frequency: Moderate (15-25% of markets)
expected_win_rate: 65-80%
confidence: Low (risky math)
```

#### value_20_30
```yaml
id: value_20_30
name: "Value 20→30"
tier: 2

parameters:
  entry_threshold: 0.20
  exit_threshold: 0.30
  stop_loss: null

math:
  profit_if_win: +50%
  loss_if_lose: -100%
  break_even_wr: 67%

notes: |
  Better than 20→25 due to improved math.
  67% break-even is more achievable.
  Give price room to bounce.

expected_frequency: Moderate (15-25% of markets)
expected_win_rate: 60-75%
confidence: Medium
```

#### value_20_35
```yaml
id: value_20_35
name: "Value 20→35"
tier: 2

parameters:
  entry_threshold: 0.20
  exit_threshold: 0.35
  stop_loss: null

math:
  profit_if_win: +75%
  loss_if_lose: -100%
  break_even_wr: 57%

notes: |
  Aggressive target improves math significantly.
  57% break-even is very achievable.
  May miss some smaller bounces.

expected_frequency: Moderate (15-25% of markets)
expected_win_rate: 55-70%
confidence: Medium
```

#### value_25_30
```yaml
id: value_25_30
name: "Value 25→30"
tier: 2

parameters:
  entry_threshold: 0.25
  exit_threshold: 0.30
  stop_loss: null

math:
  profit_if_win: +20%
  loss_if_lose: -100%
  break_even_wr: 83%

notes: |
  Tight spread, unforgiving math.
  83% WR is difficult to sustain.
  Use as comparison only.

expected_frequency: Common (25-35% of markets)
expected_win_rate: 70-85%
confidence: Low
```

#### value_25_35
```yaml
id: value_25_35
name: "Value 25→35"
tier: 2

parameters:
  entry_threshold: 0.25
  exit_threshold: 0.35
  stop_loss: null

math:
  profit_if_win: +40%
  loss_if_lose: -100%
  break_even_wr: 71%

notes: |
  Reasonable math with common entry.
  71% break-even is our target territory.
  Worth testing.

expected_frequency: Common (25-35% of markets)
expected_win_rate: 65-80%
confidence: Medium
```

#### value_30_40
```yaml
id: value_30_40
name: "Value 30→40"
tier: 2

parameters:
  entry_threshold: 0.30
  exit_threshold: 0.40
  stop_loss: null

math:
  profit_if_win: +33%
  loss_if_lose: -100%
  break_even_wr: 75%

notes: |
  Approaching mid-range territory.
  75% break-even matches our goal.
  Common entry point.

expected_frequency: Common (30-40% of markets)
expected_win_rate: 70-82%
confidence: Medium
```

---

### Tier 3: Mid-Range Reversion

**Entry range: 35% - 50%**
**Break-even win rate: 70% - 85%**
**Recommendation: TEST HYPOTHESIS**

These are the most common entries but require high win rates.

#### mid_35_45
```yaml
id: mid_35_45
name: "Mid-Range 35→45"
tier: 3

parameters:
  entry_threshold: 0.35
  exit_threshold: 0.45
  stop_loss: null

math:
  profit_if_win: +29%
  loss_if_lose: -100%
  break_even_wr: 78%

notes: |
  Common entry, needs high WR.
  Testing if mid-range mean reversion works.
  78% is achievable but not guaranteed.

expected_frequency: Very common (40-50% of markets)
expected_win_rate: 72-85%
confidence: Medium
```

#### mid_35_50
```yaml
id: mid_35_50
name: "Mid-Range 35→50"
tier: 3

parameters:
  entry_threshold: 0.35
  exit_threshold: 0.50
  stop_loss: null

math:
  profit_if_win: +43%
  loss_if_lose: -100%
  break_even_wr: 70%

notes: |
  Better math than 35→45.
  70% break-even is reasonable.
  Betting on return to equilibrium.

expected_frequency: Very common (40-50% of markets)
expected_win_rate: 68-82%
confidence: Medium
```

#### mid_40_50 ⭐ TEST
```yaml
id: mid_40_50
name: "Mid-Range 40→50"
tier: 3

parameters:
  entry_threshold: 0.40
  exit_threshold: 0.50
  stop_loss: null

math:
  profit_if_win: +25%
  loss_if_lose: -100%
  break_even_wr: 80%

notes: |
  YOUR HYPOTHESIS - WORTH TESTING
  Very common entry at 40%.
  Question: Does 40% bounce to 50% at least 80% of the time?
  This is the key question to answer empirically.

expected_frequency: Very common (40-60% of markets)
expected_win_rate: 75-88%
confidence: Unknown - must test
```

#### mid_40_55
```yaml
id: mid_40_55
name: "Mid-Range 40→55"
tier: 3

parameters:
  entry_threshold: 0.40
  exit_threshold: 0.55
  stop_loss: null

math:
  profit_if_win: +38%
  loss_if_lose: -100%
  break_even_wr: 73%

notes: |
  Better math than 40→50.
  Asking for price to cross the midpoint.
  73% break-even is achievable.

expected_frequency: Very common (40-60% of markets)
expected_win_rate: 70-83%
confidence: Medium
```

#### mid_45_50
```yaml
id: mid_45_50
name: "Mid-Range 45→50"
tier: 3

parameters:
  entry_threshold: 0.45
  exit_threshold: 0.50
  stop_loss: null

math:
  profit_if_win: +11%
  loss_if_lose: -100%
  break_even_wr: 90%

notes: |
  DANGEROUS - Very tight spread.
  Need 90% WR just to break even.
  One loss wipes out 9 wins.
  Use as negative control.

expected_frequency: Extremely common (60%+ of markets)
expected_win_rate: 85-93%
confidence: Low (risky)
```

#### mid_45_55
```yaml
id: mid_45_55
name: "Mid-Range 45→55"
tier: 3

parameters:
  entry_threshold: 0.45
  exit_threshold: 0.55
  stop_loss: null

math:
  profit_if_win: +22%
  loss_if_lose: -100%
  break_even_wr: 82%

notes: |
  Symmetrical around 50%.
  82% break-even is challenging.
  Testing pure mean reversion hypothesis.

expected_frequency: Extremely common (60%+ of markets)
expected_win_rate: 78-88%
confidence: Medium
```

---

### Tier 4: High Probability

**Entry range: 55% - 75%**
**Break-even win rate: 80% - 88%**
**Recommendation: RISKY - INCLUDE FOR COMPARISON**

These strategies bet on continuation rather than reversal.

#### high_55_65
```yaml
id: high_55_65
name: "High Prob 55→65"
tier: 4

parameters:
  entry_threshold: 0.55
  exit_threshold: 0.65
  stop_loss: null

math:
  profit_if_win: +18%
  loss_if_lose: -100%
  break_even_wr: 85%

notes: |
  Betting that slight favorite becomes stronger favorite.
  85% break-even is very demanding.
  Momentum continuation play.

expected_frequency: Very common (50-60% of markets)
expected_win_rate: 80-90%
confidence: Low
```

#### high_60_70 ⭐ TEST
```yaml
id: high_60_70
name: "High Prob 60→70"
tier: 4

parameters:
  entry_threshold: 0.60
  exit_threshold: 0.70
  stop_loss: null

math:
  profit_if_win: +17%
  loss_if_lose: -100%
  break_even_wr: 86%

notes: |
  YOUR HYPOTHESIS - WORTH TESTING
  Question: When one side is at 60%, does it reach 70% at least 86% of the time?
  This tests whether favorites tend to strengthen.

expected_frequency: Common (40-50% of markets)
expected_win_rate: 82-92%
confidence: Unknown - must test
```

#### high_65_75
```yaml
id: high_65_75
name: "High Prob 65→75"
tier: 4

parameters:
  entry_threshold: 0.65
  exit_threshold: 0.75
  stop_loss: null

math:
  profit_if_win: +15%
  loss_if_lose: -100%
  break_even_wr: 87%

notes: |
  Strong favorite getting stronger.
  87% is very hard to maintain.
  One bad day destroys weeks of gains.

expected_frequency: Common (35-45% of markets)
expected_win_rate: 83-92%
confidence: Low
```

#### high_70_80
```yaml
id: high_70_80
name: "High Prob 70→80"
tier: 4

parameters:
  entry_threshold: 0.70
  exit_threshold: 0.80
  stop_loss: null

math:
  profit_if_win: +14%
  loss_if_lose: -100%
  break_even_wr: 88%

notes: |
  Very strong favorite play.
  Extremely unforgiving math.
  Include for comparison only.

expected_frequency: Uncommon (25-35% of markets)
expected_win_rate: 84-93%
confidence: Very low
```

---

### Tier 5: Fade the Extreme

**Entry range: 75% - 95%**
**Break-even win rate: 87% - 92%**
**Recommendation: CONTRARIAN - TEST CAREFULLY**

These strategies bet AGAINST the extreme favorite.

**Note:** "Fade" means we buy the OTHER side. If YES is at 80%, we buy NO at 20%.

#### fade_75_65
```yaml
id: fade_75_65
name: "Fade Extreme 75→65"
tier: 5

parameters:
  # We BUY at this level (buying the underdog)
  entry_threshold: 0.75  # YES at 75%, so NO at 25%
  exit_threshold: 0.65   # YES falls to 65%, NO rises to 35%
  stop_loss: null
  direction: fade        # Indicates we buy the OTHER side

math:
  # Buying NO at 25%, selling at 35%
  effective_entry: 0.25
  effective_exit: 0.35
  profit_if_win: +40%
  loss_if_lose: -100%
  break_even_wr: 71%

notes: |
  Contrarian play - betting favorite weakens.
  Actually decent math (71% BE).
  Buying NO when YES is at 75%.

expected_frequency: Uncommon (20-30% of markets)
expected_win_rate: 65-78%
confidence: Medium
```

#### fade_80_70 ⭐ TEST
```yaml
id: fade_80_70
name: "Fade Extreme 80→70"
tier: 5

parameters:
  entry_threshold: 0.80  # YES at 80%, NO at 20%
  exit_threshold: 0.70   # YES falls to 70%, NO rises to 30%
  stop_loss: null
  direction: fade

math:
  # Buying NO at 20%, selling at 30%
  effective_entry: 0.20
  effective_exit: 0.30
  profit_if_win: +50%
  loss_if_lose: -100%
  break_even_wr: 67%

notes: |
  INTERESTING - This is actually a Tier 2 play in disguise!
  Buying NO at 20% (underdog) and selling at 30%.
  67% break-even is very reasonable.

expected_frequency: Uncommon (15-25% of markets)
expected_win_rate: 60-75%
confidence: Medium
```

#### fade_85_75
```yaml
id: fade_85_75
name: "Fade Extreme 85→75"
tier: 5

parameters:
  entry_threshold: 0.85  # YES at 85%, NO at 15%
  exit_threshold: 0.75   # YES falls to 75%, NO rises to 25%
  stop_loss: null
  direction: fade

math:
  # Buying NO at 15%, selling at 25%
  effective_entry: 0.15
  effective_exit: 0.25
  profit_if_win: +67%
  loss_if_lose: -100%
  break_even_wr: 60%

notes: |
  This is deep_15_25 from the other side!
  60% break-even is good.
  Question: Do 85% favorites fade to 75% at least 60% of the time?

expected_frequency: Rare (10-15% of markets)
expected_win_rate: 55-70%
confidence: Medium
```

#### fade_90_80
```yaml
id: fade_90_80
name: "Fade Extreme 90→80"
tier: 5

parameters:
  entry_threshold: 0.90  # YES at 90%, NO at 10%
  exit_threshold: 0.80   # YES falls to 80%, NO rises to 20%
  stop_loss: null
  direction: fade

math:
  # Buying NO at 10%, selling at 20%
  effective_entry: 0.10
  effective_exit: 0.20
  profit_if_win: +100%
  loss_if_lose: -100%
  break_even_wr: 50%

notes: |
  This is deep_10_20 from the other side!
  Excellent math - only need 50% WR.
  Question: Do 90% favorites fade to 80% at least 50% of the time?

expected_frequency: Very rare (5-10% of markets)
expected_win_rate: 50-65%
confidence: Medium
```

---

## Initial Strategy Portfolio

Run these 18 strategies simultaneously:

### Ultra-Deep (Tier 1 - Best Math, Rare Entries)
1. `ultra_05_10` - Entry 5%, Exit 10% ⭐ SUPER
2. `ultra_05_15` - Entry 5%, Exit 15% ⭐ SUPER
3. `ultra_05_20` - Entry 5%, Exit 20%

### Primary Deep Value (Tier 1 - Most Likely to Profit)
4. `deep_10_20` - Entry 10%, Exit 20%
5. `deep_10_25` - Entry 10%, Exit 25%
6. `deep_15_25` - Entry 15%, Exit 25%
7. `deep_15_30` - Entry 15%, Exit 30%

### Secondary Value (Tier 2 - Worth Testing)
8. `value_20_30` - Entry 20%, Exit 30%
9. `value_20_35` - Entry 20%, Exit 35%
10. `value_25_35` - Entry 25%, Exit 35%

### Mid-Range (Tier 3 - Test Hypothesis)
11. `mid_35_50` - Entry 35%, Exit 50%
12. `mid_40_50` - Entry 40%, Exit 50%
13. `mid_40_55` - Entry 40%, Exit 55%

### Control/Baseline
14. `value_20_25` - Original strategy (baseline)
15. `high_60_70` - High prob baseline

### Experimental Fade (Tier 5)
16. `fade_80_70` - Fade 80% to 70%
17. `fade_85_75` - Fade 85% to 75%
18. `fade_90_80` - Fade 90% to 80%

### Strategy Priority Based on Math

| Priority | Strategies | Break-Even WR | Why |
|----------|------------|---------------|-----|
| **HIGHEST** | ultra_05_10, ultra_05_15 | 33-50% | Best math, rare but powerful |
| **HIGH** | deep_10_20, deep_10_25 | 40-50% | Good math, more frequent |
| **MEDIUM** | deep_15_25, value_20_30 | 50-67% | Balanced |
| **TEST** | mid_40_50, high_60_70 | 80%+ | Hypothesis testing |

---

## Resolution Volatility Strategies

These strategies specifically target the extreme price movements in the final minutes.

### late_entry_05_15
```yaml
id: late_entry_05_15
name: "Late Entry Ultra Deep"
tier: 1

parameters:
  entry_threshold: 0.05
  exit_threshold: 0.15
  stop_loss: null
  time_filter: "last_5min"  # Only enter with < 5 min remaining

math:
  profit_if_win: +200%
  loss_if_lose: -100%
  break_even_wr: 33%

notes: |
  RESOLUTION VOLATILITY PLAY
  
  Only enters when:
  1. Price is at 5% (extreme)
  2. Less than 5 minutes until resolution
  
  Hypothesis: In final minutes, prices overshoot due to panic.
  A 5% price might actually have 15-20% true probability.
  
  If BTC makes any reversal, this side can spike quickly.

expected_frequency: Very rare
expected_win_rate: 35-50%
confidence: Medium - needs testing
```

### resolution_momentum_80
```yaml
id: resolution_momentum_80
name: "Resolution Momentum (Strong Side)"
tier: 4

parameters:
  entry_threshold: 0.80
  exit_threshold: 0.95
  stop_loss: null
  time_filter: "last_3min"  # Only enter with < 3 min remaining

math:
  profit_if_win: +19%
  loss_if_lose: -100%
  break_even_wr: 84%

notes: |
  RESOLUTION MOMENTUM PLAY
  
  Opposite of our usual strategy. Instead of buying the underdog,
  we're buying the favorite in the final minutes.
  
  Hypothesis: When one side is at 80% with < 3 min left,
  it usually goes to 100% (resolution wins).
  
  Risky math - need 84% WR. But the resolution momentum
  might make this achievable.
  
  EXPERIMENTAL - include for comparison only.

expected_frequency: Common in final minutes
expected_win_rate: 80-92%
confidence: Low - needs validation
```

---

## Strategy Performance Tracking

### Metrics to Track Per Strategy

| Metric | Description | Target |
|--------|-------------|--------|
| `total_trades` | Number of completed trades | ≥100 for significance |
| `win_rate` | Wins / Total | ≥75% |
| `total_pnl` | Sum of all P&L | Positive |
| `avg_pnl` | Average P&L per trade | Positive |
| `profit_factor` | Gross profit / Gross loss | ≥1.5 |
| `max_drawdown` | Worst peak-to-trough | ≤20% |
| `avg_hold_time` | Average seconds in trade | Informational |
| `take_profit_rate` | % exited at target | Higher is better |
| `resolution_exit_rate` | % held to resolution | Lower is better |

### Status Levels

| Status | Meaning | Action |
|--------|---------|--------|
| `testing` | New strategy, < 100 trades | Gather data |
| `active` | Running normally | Monitor |
| `promising` | Win rate > 70% | Increase attention |
| `champion` | Win rate > 75% for 200+ trades | Consider for live |
| `underperforming` | Win rate < break-even | Monitor closely |
| `retired` | Consistently unprofitable | Stop running |

---

## Hybrid Strategy (Future)

### Concept

Instead of all-or-nothing exits:
1. Enter at deep value (10-15%)
2. Sell HALF at first target (25%)
3. Let other half ride to resolution

### Example

```
Entry: Buy 100 shares of YES at 10% ($10 cost)

Scenario A - Partial win + Resolution win:
  - Sell 50 shares at 25% → $12.50 (+$2.50)
  - Hold 50 shares → YES wins, 50 × $1.00 = $50
  - Total: $62.50 on $10 investment = +525%

Scenario B - Partial win + Resolution loss:
  - Sell 50 shares at 25% → $12.50 (+$2.50)
  - Hold 50 shares → YES loses, 50 × $0.00 = $0
  - Total: $12.50 on $10 investment = +25%

Scenario C - No partial, Resolution loss:
  - Never hits 25%
  - YES loses → $0
  - Total: $0 on $10 investment = -100%
```

### Benefits
- Locks in guaranteed profit when target hit
- Still exposed to massive upside
- Reduces average loss

### Implementation (Later)
```python
class HybridStrategy(BaseStrategy):
    def __init__(self):
        self.entry = 0.10
        self.partial_exit = 0.25
        self.partial_size = 0.50  # Sell 50% at first target
        self.final_exit = "resolution"  # Hold rest to end
```

---

*Document Version: 1.0*
*Last Updated: January 2025*
