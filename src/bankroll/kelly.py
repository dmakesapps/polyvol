"""
Kelly Criterion Position Sizing.
Calculates optimal bet sizes based on edge and win rate.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class BetSize:
    """Recommended bet size."""
    amount: float
    percentage: float
    kelly_fraction: float
    confidence: str
    reasoning: str


def calculate_kelly(win_rate: float, win_loss_ratio: float) -> float:
    """
    Calculate the Kelly Criterion percentage.
    
    Kelly % = W - [(1 - W) / R]
    
    Args:
        win_rate: Probability of winning (0-1)
        win_loss_ratio: Average win / Average loss
        
    Returns:
        Kelly percentage (can be negative = don't bet)
    """
    if win_loss_ratio <= 0:
        return 0.0
    
    kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
    return kelly


def fractional_kelly(
    bankroll: float,
    win_rate: float,
    win_loss_ratio: float,
    fraction: float = 0.5,
    min_bet_pct: float = 0.03,
    max_bet_pct: float = 0.15
) -> BetSize:
    """
    Calculate bet size using fractional Kelly.
    
    Args:
        bankroll: Current bankroll
        win_rate: Estimated probability of winning (0-1)
        win_loss_ratio: Average win / Average loss
        fraction: Kelly fraction (0.5 = half Kelly)
        min_bet_pct: Minimum bet as percentage of bankroll
        max_bet_pct: Maximum bet as percentage of bankroll
        
    Returns:
        BetSize with recommended amount and percentage
    """
    kelly = calculate_kelly(win_rate, win_loss_ratio)
    
    # Kelly can be negative - don't bet
    if kelly <= 0:
        return BetSize(
            amount=0,
            percentage=0,
            kelly_fraction=kelly,
            confidence="none",
            reasoning=f"Negative Kelly ({kelly:.1%}). Math doesn't support this bet."
        )
    
    # Apply fraction
    bet_pct = kelly * fraction
    
    # Apply bounds
    original_pct = bet_pct
    bet_pct = max(min_bet_pct, min(bet_pct, max_bet_pct))
    
    # Calculate amount
    amount = bankroll * bet_pct
    
    # Determine confidence
    if kelly >= 0.20:
        confidence = "high"
    elif kelly >= 0.10:
        confidence = "medium"
    else:
        confidence = "low"
    
    reasoning = f"Kelly={kelly:.1%}, Fraction={fraction}, Adjusted={bet_pct:.1%}"
    if bet_pct != original_pct:
        reasoning += f" (clamped from {original_pct:.1%})"
    
    return BetSize(
        amount=amount,
        percentage=bet_pct,
        kelly_fraction=kelly,
        confidence=confidence,
        reasoning=reasoning
    )


def calculate_bet_for_strategy(
    bankroll: float,
    entry_price: float,
    exit_price: float,
    estimated_win_rate: Optional[float] = None,
    fraction: float = 0.5
) -> BetSize:
    """
    Calculate bet size for a specific strategy.
    
    Args:
        bankroll: Current bankroll
        entry_price: Entry price (e.g., 0.10 for 10%)
        exit_price: Exit price (e.g., 0.20 for 20%)
        estimated_win_rate: Optional estimated win rate
        fraction: Kelly fraction
        
    Returns:
        BetSize recommendation
    """
    # Calculate profit if win
    profit_pct = (exit_price - entry_price) / entry_price
    
    # Loss is always 100% (position goes to 0)
    loss_pct = 1.0
    
    # Win/loss ratio
    win_loss_ratio = profit_pct / loss_pct
    
    # If no estimated win rate, use break-even as minimum
    if estimated_win_rate is None:
        # Be conservative - assume we're slightly above break-even
        break_even_wr = loss_pct / (loss_pct + profit_pct)
        estimated_win_rate = break_even_wr + 0.05  # Assume 5% edge
    
    return fractional_kelly(
        bankroll=bankroll,
        win_rate=estimated_win_rate,
        win_loss_ratio=win_loss_ratio,
        fraction=fraction
    )


# Pre-calculated Kelly values for reference
STRATEGY_KELLY = {
    "ultra_05_15": {"entry": 0.05, "exit": 0.15, "profit": 2.0, "be_wr": 0.33, "kelly_at_45": 0.175},
    "ultra_05_10": {"entry": 0.05, "exit": 0.10, "profit": 1.0, "be_wr": 0.50, "kelly_at_55": 0.10},
    "deep_10_20": {"entry": 0.10, "exit": 0.20, "profit": 1.0, "be_wr": 0.50, "kelly_at_60": 0.20},
    "deep_10_25": {"entry": 0.10, "exit": 0.25, "profit": 1.5, "be_wr": 0.40, "kelly_at_55": 0.25},
    "deep_15_25": {"entry": 0.15, "exit": 0.25, "profit": 0.67, "be_wr": 0.60, "kelly_at_65": 0.13},
    "value_20_25": {"entry": 0.20, "exit": 0.25, "profit": 0.25, "be_wr": 0.80, "kelly_at_75": -0.25},
    "mid_40_50": {"entry": 0.40, "exit": 0.50, "profit": 0.25, "be_wr": 0.80, "kelly_at_80": 0.00},
}
