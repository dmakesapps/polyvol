"""
Core configuration module.
Loads settings from YAML and environment variables.
"""
import os
from pathlib import Path
from typing import Any, Optional, List

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


class StrategyConfig(BaseModel):
    """Configuration for a single strategy."""
    id: str
    entry: float
    exit: float
    tier: int
    enabled: bool = True
    direction: str = "normal"  # normal or fade


class VaultConfig(BaseModel):
    """Vault (profit protection) settings."""
    enabled: bool = True
    deposit_rate: float = 0.20


class RiskConfig(BaseModel):
    """Risk management settings."""
    max_drawdown: float = 0.25
    max_daily_loss: float = 0.15
    max_consecutive_losses: int = 5
    cooldown_minutes: int = 15


class BankrollConfig(BaseModel):
    """Bankroll management settings."""
    initial: float = 100.0
    sizing_method: str = "fractional_kelly"
    kelly_fraction: float = 0.50
    max_bet_pct: float = 0.15
    min_bet_pct: float = 0.03
    vault: VaultConfig = VaultConfig()
    risk: RiskConfig = RiskConfig()


class CollectionConfig(BaseModel):
    """Data collection settings."""
    poll_interval: int = 5
    assets: List[str] = ["BTC", "ETH", "SOL", "XRP"]
    market_type: str = "15min"


class ExitConfig(BaseModel):
    """Exit rule settings."""
    take_profit: bool = True
    resolution_exit_threshold: int = 120
    time_stop_threshold: int = 600


class AnalysisConfig(BaseModel):
    """Analysis settings."""
    interval: int = 3600
    min_trades_significance: int = 50


class Config(BaseModel):
    """Main configuration container."""
    mode: str = "paper"
    log_level: str = "INFO"
    database_path: str = "data/evolution.db"
    collection: CollectionConfig = CollectionConfig()
    strategies: List[StrategyConfig] = []
    bankroll: BankrollConfig = BankrollConfig()
    exits: ExitConfig = ExitConfig()
    analysis: AnalysisConfig = AnalysisConfig()
    
    # Optional API keys (loaded from environment)
    openrouter_api_key: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    
    # Polymarket Trading Credentials
    poly_private_key: Optional[str] = None  # Wallet private key for signing
    poly_api_key: Optional[str] = None      # CLOB API Key
    poly_api_secret: Optional[str] = None   # CLOB API Secret
    poly_passphrase: Optional[str] = None   # CLOB Passphrase


def load_config(config_path: str = "config/settings.yaml") -> Config:
    """
    Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to the YAML config file
        
    Returns:
        Config object with all settings
    """
    # Load environment variables
    env_path = Path("config/.env")
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # Try default .env
    
    # Load YAML config
    config_data: dict[str, Any] = {}
    yaml_path = Path(config_path)
    
    if yaml_path.exists():
        with open(yaml_path, "r") as f:
            raw_config = yaml.safe_load(f)
            if raw_config:
                # Flatten the 'system' section into root
                if "system" in raw_config:
                    config_data.update(raw_config.pop("system"))
                config_data.update(raw_config)
    
    # Parse strategies
    strategies = []
    for s in config_data.get("strategies", []):
        strategies.append(StrategyConfig(**s))
    config_data["strategies"] = strategies
    
    # Add environment variables
    config_data["openrouter_api_key"] = os.getenv("OPENROUTER_API_KEY")
    config_data["discord_webhook_url"] = os.getenv("DISCORD_WEBHOOK_URL")
    
    # Polymarket trading credentials
    config_data["poly_private_key"] = os.getenv("POLY_PRIVATE_KEY")
    config_data["poly_api_key"] = os.getenv("POLY_API_KEY")
    config_data["poly_api_secret"] = os.getenv("POLY_API_SECRET")
    config_data["poly_passphrase"] = os.getenv("POLY_PASSPHRASE")
    
    # Override database path from env if set
    if os.getenv("DATABASE_PATH"):
        config_data["database_path"] = os.getenv("DATABASE_PATH")
    
    # Override mode from env if set (paper, live, testnet)
    if os.getenv("MODE"):
        config_data["mode"] = os.getenv("MODE")
    
    return Config(**config_data)


# Global config instance (lazy loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
