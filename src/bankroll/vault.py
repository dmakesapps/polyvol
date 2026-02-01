"""
Vault System.
Protects a portion of profits by moving them to a safe "vault".
The vault is never risked in trades.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import structlog


logger = structlog.get_logger()


@dataclass
class VaultState:
    """Current state of the vault system."""
    bankroll: float
    vault: float
    initial_bankroll: float
    vault_deposit_rate: float
    
    @property
    def total_equity(self) -> float:
        """Total value = bankroll + vault."""
        return self.bankroll + self.vault
    
    @property
    def total_return(self) -> float:
        """Total return percentage."""
        if self.initial_bankroll <= 0:
            return 0.0
        return (self.total_equity - self.initial_bankroll) / self.initial_bankroll
    
    @property
    def vault_percentage(self) -> float:
        """Percentage of equity in vault."""
        if self.total_equity <= 0:
            return 0.0
        return self.vault / self.total_equity


@dataclass
class TradeResult:
    """Result of processing a trade through the vault system."""
    pnl: float
    is_win: bool
    bankroll_change: float
    vault_deposit: float
    new_bankroll: float
    new_vault: float


class VaultBankroll:
    """
    Bankroll management with protected vault.
    
    After every winning trade, a portion of profits goes to the vault.
    The vault is never risked - it's protected money.
    Losses only come from the active bankroll.
    """
    
    def __init__(
        self,
        initial_bankroll: float = 100.0,
        vault_deposit_rate: float = 0.20,
        emergency_withdrawal_threshold: float = 0.20
    ):
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.vault = 0.0
        self.vault_deposit_rate = vault_deposit_rate
        self.emergency_threshold = emergency_withdrawal_threshold
        
        # Track peaks for drawdown
        self.peak_equity = initial_bankroll
        self.peak_bankroll = initial_bankroll
        
        # History
        self.trade_history: list[dict] = []
    
    @property
    def total_equity(self) -> float:
        """Total value = bankroll + vault."""
        return self.bankroll + self.vault
    
    @property
    def total_return(self) -> float:
        """Total return percentage."""
        return (self.total_equity - self.initial_bankroll) / self.initial_bankroll
    
    @property
    def current_drawdown(self) -> float:
        """Current drawdown from peak equity."""
        if self.peak_equity <= 0:
            return 0.0
        return (self.peak_equity - self.total_equity) / self.peak_equity
    
    @property
    def bankroll_drawdown(self) -> float:
        """Current drawdown of bankroll only."""
        if self.peak_bankroll <= 0:
            return 0.0
        return (self.peak_bankroll - self.bankroll) / self.peak_bankroll
    
    def process_trade(self, pnl: float, is_win: bool) -> TradeResult:
        """
        Process a completed trade.
        
        Winning trades: deposit portion to vault
        Losing trades: deduct from bankroll only
        
        Args:
            pnl: Profit/loss in dollars
            is_win: Whether the trade was a win
            
        Returns:
            TradeResult with updated balances
        """
        vault_deposit = 0.0
        
        if is_win and pnl > 0:
            # Deposit portion of profit to vault
            vault_deposit = pnl * self.vault_deposit_rate
            self.vault += vault_deposit
            self.bankroll += (pnl - vault_deposit)
            
            logger.debug(
                "vault.profit_deposited",
                pnl=pnl,
                vault_deposit=vault_deposit,
                bankroll_add=pnl - vault_deposit
            )
        else:
            # Losses come from bankroll only
            self.bankroll += pnl  # pnl is negative
            
            logger.debug(
                "vault.loss_applied",
                pnl=pnl,
                new_bankroll=self.bankroll
            )
        
        # Update peaks
        self.peak_equity = max(self.peak_equity, self.total_equity)
        self.peak_bankroll = max(self.peak_bankroll, self.bankroll)
        
        # Record history
        self.trade_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "pnl": pnl,
            "is_win": is_win,
            "vault_deposit": vault_deposit,
            "bankroll": self.bankroll,
            "vault": self.vault,
            "total_equity": self.total_equity
        })
        
        # Check for emergency withdrawal needed
        self._check_emergency()
        
        return TradeResult(
            pnl=pnl,
            is_win=is_win,
            bankroll_change=pnl - vault_deposit if is_win else pnl,
            vault_deposit=vault_deposit,
            new_bankroll=self.bankroll,
            new_vault=self.vault
        )
    
    def _check_emergency(self) -> None:
        """
        Check if emergency vault withdrawal is needed.
        If bankroll drops below threshold of total equity, 
        withdraw from vault to maintain trading capital.
        """
        if self.total_equity <= 0:
            return
        
        bankroll_ratio = self.bankroll / self.total_equity
        
        if bankroll_ratio < self.emergency_threshold and self.vault > 0:
            # Calculate how much to withdraw
            target_bankroll = self.total_equity * self.emergency_threshold
            withdrawal = min(target_bankroll - self.bankroll, self.vault)
            
            if withdrawal > 0:
                self.vault -= withdrawal
                self.bankroll += withdrawal
                
                logger.warning(
                    "vault.emergency_withdrawal",
                    withdrawal=withdrawal,
                    new_bankroll=self.bankroll,
                    new_vault=self.vault,
                    reason=f"Bankroll was {bankroll_ratio:.1%} of equity, below {self.emergency_threshold:.1%} threshold"
                )
    
    def get_state(self) -> VaultState:
        """Get current vault state."""
        return VaultState(
            bankroll=self.bankroll,
            vault=self.vault,
            initial_bankroll=self.initial_bankroll,
            vault_deposit_rate=self.vault_deposit_rate
        )
    
    def get_status(self) -> dict:
        """Get current status as a dictionary."""
        return {
            "bankroll": round(self.bankroll, 2),
            "vault": round(self.vault, 2),
            "total_equity": round(self.total_equity, 2),
            "total_return": f"{self.total_return * 100:.1f}%",
            "drawdown": f"{self.current_drawdown * 100:.1f}%",
            "trades_processed": len(self.trade_history)
        }
    
    def reset(self) -> None:
        """Reset to initial state."""
        self.bankroll = self.initial_bankroll
        self.vault = 0.0
        self.peak_equity = self.initial_bankroll
        self.peak_bankroll = self.initial_bankroll
        self.trade_history = []
        
        logger.info("vault.reset", initial_bankroll=self.initial_bankroll)
