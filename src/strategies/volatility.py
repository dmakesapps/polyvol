"""
Volatility Trading Strategies.
Implementations of all 18 strategies from the documentation.
"""
from .base import BaseStrategy


class VolatilityStrategy(BaseStrategy):
    """
    Standard volatility bounce strategy.
    Buys when price drops to entry threshold, sells at exit threshold.
    """
    pass  # Uses all base class functionality


def create_strategy(config: dict) -> BaseStrategy:
    """
    Factory function to create a strategy from config.
    
    Args:
        config: Strategy configuration dict with id, entry, exit, tier, direction
        
    Returns:
        Configured strategy instance
    """
    strategy_id = config["id"]
    entry = config["entry"]
    exit_threshold = config["exit"]
    tier = config.get("tier", 1)
    direction = config.get("direction", "normal")
    
    # Generate a readable name
    if direction == "fade":
        name = f"Fade {int(entry*100)}→{int(exit_threshold*100)}"
    else:
        name = f"Value {int(entry*100)}→{int(exit_threshold*100)}"
    
    return VolatilityStrategy(
        strategy_id=strategy_id,
        name=name,
        tier=tier,
        entry_threshold=entry,
        exit_threshold=exit_threshold,
        direction=direction
    )


def create_all_strategies(configs: list[dict]) -> list[BaseStrategy]:
    """
    Create all strategies from a list of configs.
    
    Args:
        configs: List of strategy configuration dicts
        
    Returns:
        List of strategy instances
    """
    return [
        create_strategy(config) 
        for config in configs 
        if config.get("enabled", True)
    ]


# Pre-defined strategy configurations (matches docs)
DEFAULT_STRATEGIES = [
    # Tier 1: Ultra-Deep (BEST MATH)
    {"id": "ultra_05_10", "entry": 0.05, "exit": 0.10, "tier": 1},
    {"id": "ultra_05_15", "entry": 0.05, "exit": 0.15, "tier": 1},
    {"id": "ultra_05_20", "entry": 0.05, "exit": 0.20, "tier": 1},
    
    # Tier 1: Deep Value (RECOMMENDED)
    {"id": "deep_10_20", "entry": 0.10, "exit": 0.20, "tier": 1},
    {"id": "deep_10_25", "entry": 0.10, "exit": 0.25, "tier": 1},
    {"id": "deep_15_25", "entry": 0.15, "exit": 0.25, "tier": 1},
    {"id": "deep_15_30", "entry": 0.15, "exit": 0.30, "tier": 1},
    
    # Tier 2: Value
    {"id": "value_20_25", "entry": 0.20, "exit": 0.25, "tier": 2},
    {"id": "value_20_30", "entry": 0.20, "exit": 0.30, "tier": 2},
    {"id": "value_20_35", "entry": 0.20, "exit": 0.35, "tier": 2},
    
    # Tier 3: Mid-Range
    {"id": "mid_35_50", "entry": 0.35, "exit": 0.50, "tier": 3},
    {"id": "mid_40_50", "entry": 0.40, "exit": 0.50, "tier": 3},
    {"id": "mid_40_55", "entry": 0.40, "exit": 0.55, "tier": 3},
    
    # Tier 4: High Probability
    {"id": "high_60_70", "entry": 0.60, "exit": 0.70, "tier": 4},
    
    # Tier 5: Fade
    {"id": "fade_80_70", "entry": 0.80, "exit": 0.70, "tier": 5, "direction": "fade"},
    {"id": "fade_85_75", "entry": 0.85, "exit": 0.75, "tier": 5, "direction": "fade"},
    {"id": "fade_90_80", "entry": 0.90, "exit": 0.80, "tier": 5, "direction": "fade"},
]
