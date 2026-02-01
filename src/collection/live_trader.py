"""
Live Trading Client for Polymarket.
Uses the official SDK for authenticated order execution.
"""
import structlog
from typing import Optional
from decimal import Decimal

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

logger = structlog.get_logger()


class LiveTrader:
    """
    Handles real order execution on Polymarket.
    This class wraps the official py-clob-client SDK.
    """
    
    # Polymarket CLOB endpoints
    POLYGON_MAINNET = "https://clob.polymarket.com"
    POLYGON_AMOY = "https://clob-staging.polymarket.com"  # Testnet
    
    def __init__(
        self,
        private_key: str,
        api_key: str,
        api_secret: str,
        passphrase: str,
        chain_id: int = 137,  # Polygon Mainnet
        testnet: bool = False
    ):
        """
        Initialize the live trader.
        
        Args:
            private_key: Wallet private key (for signing orders)
            api_key: CLOB API Key
            api_secret: CLOB API Secret  
            passphrase: CLOB Passphrase
            chain_id: Chain ID (137 for Polygon Mainnet)
            testnet: If True, use staging/testnet endpoint
        """
        self.host = self.POLYGON_AMOY if testnet else self.POLYGON_MAINNET
        self.chain_id = chain_id
        
        # Initialize the official CLOB client
        self.client = ClobClient(
            host=self.host,
            chain_id=self.chain_id,
            key=private_key,
            creds={
                "apiKey": api_key,
                "secret": api_secret,
                "passphrase": passphrase
            }
        )
        
        logger.info(
            "live_trader.initialized",
            host=self.host,
            chain_id=self.chain_id
        )
    
    async def get_balance(self) -> dict:
        """
        Get the current wallet balance.
        
        Returns:
            Balance information
        """
        try:
            balance = self.client.get_balance_allowance()
            logger.info("live_trader.balance", balance=balance)
            return balance
        except Exception as e:
            logger.error("live_trader.balance.error", error=str(e))
            return {"error": str(e)}
    
    async def buy_yes(
        self,
        token_id: str,
        price: float,
        size: float
    ) -> Optional[str]:
        """
        Place a BUY order for YES shares.
        
        Args:
            token_id: The YES token ID
            price: Price per share (e.g., 0.20 for 20%)
            size: Number of shares to buy
            
        Returns:
            Order ID if successful, None otherwise
        """
        return await self._place_order(
            token_id=token_id,
            side=BUY,
            price=price,
            size=size
        )
    
    async def sell_yes(
        self,
        token_id: str,
        price: float,
        size: float
    ) -> Optional[str]:
        """
        Place a SELL order for YES shares (exit position).
        
        Args:
            token_id: The YES token ID
            price: Price per share
            size: Number of shares to sell
            
        Returns:
            Order ID if successful, None otherwise
        """
        return await self._place_order(
            token_id=token_id,
            side=SELL,
            price=price,
            size=size
        )
    
    async def buy_no(
        self,
        token_id: str,
        price: float,
        size: float
    ) -> Optional[str]:
        """
        Place a BUY order for NO shares (fade/short strategy).
        
        Args:
            token_id: The NO token ID
            price: Price per share
            size: Number of shares to buy
            
        Returns:
            Order ID if successful, None otherwise
        """
        return await self._place_order(
            token_id=token_id,
            side=BUY,
            price=price,
            size=size
        )
    
    async def sell_no(
        self,
        token_id: str,
        price: float,
        size: float
    ) -> Optional[str]:
        """
        Place a SELL order for NO shares (exit fade position).
        
        Args:
            token_id: The NO token ID
            price: Price per share
            size: Number of shares to sell
            
        Returns:
            Order ID if successful, None otherwise
        """
        return await self._place_order(
            token_id=token_id,
            side=SELL,
            price=price,
            size=size
        )
    
    async def _place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        order_type: str = "GTC"  # Good Till Cancel
    ) -> Optional[str]:
        """
        Internal method to place an order.
        
        Args:
            token_id: Token ID to trade
            side: BUY or SELL
            price: Price per share
            size: Number of shares
            order_type: Order type (GTC, FOK, etc.)
            
        Returns:
            Order ID if successful
        """
        try:
            # Build the order
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=side,
                fee_rate_bps=0,  # Maker orders have 0 fees on Polymarket
            )
            
            # Create signed order
            signed_order = self.client.create_order(order_args)
            
            # Submit to CLOB
            response = self.client.post_order(signed_order, OrderType.GTC)
            
            order_id = response.get("orderID") or response.get("id")
            
            logger.info(
                "live_trader.order.placed",
                token_id=token_id,
                side=side,
                price=price,
                size=size,
                order_id=order_id
            )
            
            return order_id
            
        except Exception as e:
            logger.error(
                "live_trader.order.error",
                token_id=token_id,
                side=side,
                price=price,
                size=size,
                error=str(e)
            )
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order.
        
        Args:
            order_id: The order ID to cancel
            
        Returns:
            True if successful
        """
        try:
            self.client.cancel(order_id)
            logger.info("live_trader.order.cancelled", order_id=order_id)
            return True
        except Exception as e:
            logger.error("live_trader.cancel.error", order_id=order_id, error=str(e))
            return False
    
    async def get_open_orders(self) -> list:
        """
        Get all open orders.
        
        Returns:
            List of open orders
        """
        try:
            orders = self.client.get_orders()
            return orders
        except Exception as e:
            logger.error("live_trader.get_orders.error", error=str(e))
            return []


def create_live_trader(config) -> Optional[LiveTrader]:
    """
    Factory function to create a LiveTrader from config.
    
    Args:
        config: Config object with poly_* credentials
        
    Returns:
        LiveTrader instance or None if credentials missing
    """
    if not all([
        config.poly_private_key,
        config.poly_api_key,
        config.poly_api_secret,
        config.poly_passphrase
    ]):
        logger.warning("live_trader.missing_credentials")
        return None
    
    return LiveTrader(
        private_key=config.poly_private_key,
        api_key=config.poly_api_key,
        api_secret=config.poly_api_secret,
        passphrase=config.poly_passphrase,
        testnet=(config.mode == "testnet")
    )
