"""
Live Trading Client for Polymarket CLOB.
Direct HTTP implementation following official API spec.
Works with Python 3.9+ without requiring py-clob-client SDK.
"""
import hashlib
import hmac
import time
import json
from typing import Optional, Literal
from datetime import datetime

import httpx
import structlog
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

logger = structlog.get_logger()


# Constants
CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon Mainnet


class LiveTrader:
    """
    Handles real order execution on Polymarket CLOB.
    Uses direct HTTP calls with proper authentication.
    """
    
    def __init__(
        self,
        private_key: str,
        api_key: str,
        api_secret: str,
        passphrase: str,
        host: str = CLOB_HOST,
        chain_id: int = CHAIN_ID
    ):
        """
        Initialize the live trader.
        
        Args:
            private_key: Wallet private key (for signing orders)
            api_key: CLOB API Key
            api_secret: CLOB API Secret  
            passphrase: CLOB Passphrase
            host: CLOB API host
            chain_id: Chain ID (137 for Polygon)
        """
        self.host = host
        self.chain_id = chain_id
        self.private_key = private_key
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        
        # Initialize web3 account for signing
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            "live_trader.initialized",
            host=self.host,
            chain_id=self.chain_id,
            address=self.address
        )
    
    async def connect(self) -> None:
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.host,
            timeout=30.0
        )
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _generate_l2_headers(
        self,
        method: str,
        path: str,
        body: str = ""
    ) -> dict:
        """
        Generate L2 authentication headers for API requests.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API path
            body: Request body (JSON string)
            
        Returns:
            Headers dict with authentication
        """
        timestamp = str(int(time.time()))
        
        # Create signature message
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "POLY_API_KEY": self.api_key,
            "POLY_SIGNATURE": signature,
            "POLY_TIMESTAMP": timestamp,
            "POLY_PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }
    
    def _sign_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: Literal["BUY", "SELL"],
        nonce: Optional[int] = None
    ) -> dict:
        """
        Create and sign an order.
        
        Args:
            token_id: Market token ID
            price: Price per share
            size: Number of shares
            side: BUY or SELL
            nonce: Optional nonce (uses timestamp if not provided)
            
        Returns:
            Signed order dict
        """
        if nonce is None:
            nonce = int(time.time() * 1000)
        
        # Convert to proper format for signing
        price_raw = int(price * 1e6)  # Price in USDC (6 decimals)
        size_raw = int(size * 1e6)    # Size in shares
        
        # Order struct according to Polymarket spec
        order = {
            "salt": nonce,
            "maker": self.address,
            "signer": self.address,
            "taker": "0x0000000000000000000000000000000000000000",
            "tokenId": token_id,
            "makerAmount": str(size_raw) if side == "SELL" else str(price_raw * size_raw // 1e6),
            "takerAmount": str(price_raw * size_raw // 1e6) if side == "SELL" else str(size_raw),
            "expiration": "0",
            "nonce": str(nonce),
            "feeRateBps": "0",
            "side": 0 if side == "BUY" else 1,
            "signatureType": 0  # EOA
        }
        
        # Create EIP-712 typed data hash and sign
        # Simplified: sign the order hash
        order_hash = Web3.solidity_keccak(
            ['uint256', 'address', 'address', 'address', 'uint256', 'uint256', 'uint256', 'uint256', 'uint256', 'uint256', 'uint8', 'uint8'],
            [
                nonce,
                self.address,
                self.address,
                "0x0000000000000000000000000000000000000000",
                int(token_id) if token_id.isdigit() else int(token_id, 16),
                int(order["makerAmount"]),
                int(order["takerAmount"]),
                0,  # expiration
                nonce,
                0,  # feeRateBps
                order["side"],
                0   # signatureType
            ]
        )
        
        message = encode_defunct(order_hash)
        signed = self.account.sign_message(message)
        
        order["signature"] = signed.signature.hex()
        
        return order
    
    async def get_balance(self) -> dict:
        """Get current balance and allowance."""
        try:
            path = "/balance-allowance"
            headers = self._generate_l2_headers("GET", path)
            
            response = await self._client.get(path, headers=headers)
            response.raise_for_status()
            return response.json()
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
            price: Price per share (0.0 - 1.0)
            size: Number of shares to buy
            
        Returns:
            Order ID if successful
        """
        return await self._place_order(token_id, price, size, "BUY")
    
    async def sell_yes(
        self,
        token_id: str,
        price: float,
        size: float
    ) -> Optional[str]:
        """Place a SELL order for YES shares."""
        return await self._place_order(token_id, price, size, "SELL")
    
    async def buy_no(
        self,
        token_id: str,
        price: float,
        size: float
    ) -> Optional[str]:
        """Place a BUY order for NO shares."""
        return await self._place_order(token_id, price, size, "BUY")
    
    async def sell_no(
        self,
        token_id: str,
        price: float,
        size: float
    ) -> Optional[str]:
        """Place a SELL order for NO shares."""
        return await self._place_order(token_id, price, size, "SELL")
    
    async def _place_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: Literal["BUY", "SELL"]
    ) -> Optional[str]:
        """
        Internal method to place an order.
        
        Args:
            token_id: Token ID
            price: Price per share
            size: Number of shares
            side: BUY or SELL
            
        Returns:
            Order ID if successful
        """
        try:
            # Create signed order
            signed_order = self._sign_order(token_id, price, size, side)
            
            # Submit order
            path = "/order"
            body = json.dumps({
                "order": signed_order,
                "orderType": "GTC",  # Good Till Cancel
                "owner": self.address
            })
            
            headers = self._generate_l2_headers("POST", path, body)
            
            response = await self._client.post(path, headers=headers, content=body)
            response.raise_for_status()
            
            result = response.json()
            order_id = result.get("orderID") or result.get("id")
            
            logger.info(
                "live_trader.order.placed",
                token_id=token_id,
                side=side,
                price=price,
                size=size,
                order_id=order_id
            )
            
            return order_id
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            logger.error(
                "live_trader.order.http_error",
                token_id=token_id,
                side=side,
                price=price,
                size=size,
                status_code=e.response.status_code,
                error=error_detail
            )
            return None
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
        """Cancel an existing order."""
        try:
            path = f"/order/{order_id}"
            headers = self._generate_l2_headers("DELETE", path)
            
            response = await self._client.delete(path, headers=headers)
            response.raise_for_status()
            
            logger.info("live_trader.order.cancelled", order_id=order_id)
            return True
        except Exception as e:
            logger.error("live_trader.cancel.error", order_id=order_id, error=str(e))
            return False
    
    async def get_open_orders(self) -> list:
        """Get all open orders."""
        try:
            path = "/orders"
            headers = self._generate_l2_headers("GET", path)
            
            response = await self._client.get(path, headers=headers)
            response.raise_for_status()
            return response.json()
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
        logger.warning("live_trader.missing_credentials", 
                      has_key=bool(config.poly_private_key),
                      has_api_key=bool(config.poly_api_key),
                      has_secret=bool(config.poly_api_secret),
                      has_passphrase=bool(config.poly_passphrase))
        return None
    
    # Use staging for testnet mode
    host = CLOB_HOST
    if config.mode == "testnet":
        host = "https://clob-staging.polymarket.com"
    
    return LiveTrader(
        private_key=config.poly_private_key,
        api_key=config.poly_api_key,
        api_secret=config.poly_api_secret,
        passphrase=config.poly_passphrase,
        host=host
    )
