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
        funder_address: Optional[str] = None,
        signature_type: int = 1,  # 1 = Polymarket Proxy (for accounts created on polymarket.com)
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
            funder_address: The Polymarket proxy wallet address (for Type 1)
            signature_type: 0=EOA, 1=PolyProxy, 2=MagicLink
            host: CLOB API host
            chain_id: Chain ID (137 for Polygon)
        """
        self.host = host
        self.chain_id = chain_id
        self.private_key = private_key
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.signature_type = signature_type
        
        # Initialize web3 account for signing
        self.account = Account.from_key(private_key)
        self.signer_address = self.account.address
        
        # Funder is either provided (proxy) or same as signer (EOA)
        self.funder_address = funder_address or self.signer_address
        
        # For compatibility, keep self.address pointing to funder
        self.address = self.funder_address
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            "live_trader.initialized",
            host=self.host,
            chain_id=self.chain_id,
            signer=self.signer_address,
            funder=self.funder_address,
            signature_type=self.signature_type
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
        Matches the official py-clob-client implementation.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API path
            body: Request body (JSON string)
            
        Returns:
            Headers dict with authentication
        """
        import base64
        
        timestamp = str(int(time.time()))
        
        # Create signature message: timestamp + method + path + body
        # Body needs single quotes replaced with double quotes for compatibility
        message = f"{timestamp}{method}{path}"
        if body:
            message += body.replace("'", '"')
        
        # Decode the URL-safe base64 secret
        base64_secret = base64.urlsafe_b64decode(self.api_secret)
        
        # Sign with HMAC-SHA256 and encode as URL-safe Base64
        h = hmac.new(base64_secret, message.encode('utf-8'), hashlib.sha256)
        signature = base64.urlsafe_b64encode(h.digest()).decode('utf-8')
        
        return {
            "POLY_ADDRESS": self.signer_address,  # Required: signer address (must match the key derivation)
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
        """
        if nonce is None:
            nonce = int(time.time() * 1000)
        
        # Convert to proper format for signing
        price_raw = int(price * 1e6)  # Price in USDC (6 decimals)
        size_raw = int(size * 1e6)    # Size in shares
        
        # Calculate amounts
        maker_amount = size_raw if side == "SELL" else int(price_raw * size_raw // int(1e6))
        taker_amount = int(price_raw * size_raw // int(1e6)) if side == "SELL" else size_raw
        
        # 1. Define EIP-712 Domain and Types
        domain = {
            "name": "Polymarket CTF Exchange",
            "version": "1",
            "chainId": self.chain_id,
            "verifyingContract": "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
        }
        
        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Order": [
                {"name": "salt", "type": "uint256"},
                {"name": "maker", "type": "address"},
                {"name": "signer", "type": "address"},
                {"name": "taker", "type": "address"},
                {"name": "tokenId", "type": "uint256"},
                {"name": "makerAmount", "type": "uint256"},
                {"name": "takerAmount", "type": "uint256"},
                {"name": "expiration", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "feeRateBps", "type": "uint256"},
                {"name": "side", "type": "uint8"},
                {"name": "signatureType", "type": "uint256"},
            ]
        }
        
        # 2. Define the message (matching the types)
        # Note: All numbers for EIP-712 signing in Python usually need to be int or str depending on library.
        # eth_account sign_typed_data usually handles ints fine.
        message = {
            "salt": nonce,
            "maker": self.funder_address,
            "signer": self.signer_address,
            "taker": "0x0000000000000000000000000000000000000000",
            "tokenId": int(token_id) if token_id.isdigit() else int(token_id, 16),
            "makerAmount": maker_amount,
            "takerAmount": taker_amount,
            "expiration": 0,
            "nonce": nonce,
            "feeRateBps": 0,
            "side": 0 if side == "BUY" else 1,
            "signatureType": self.signature_type
        }
        
        # 3. Sign using encode_typed_data (Standard EIP-712)
        from eth_account.messages import encode_typed_data
        
        full_data = {
            "types": types,
            "domain": domain,
            "primaryType": "Order",
            "message": message
        }
        
        signable = encode_typed_data(full_message=full_data)
        signed = self.account.sign_message(signable)
        signature = signed.signature.hex()
        
        # 4. Construct the API payload
        # The payload structure is 'order' dict. 
        # Crucially: All values must be STRINGS for the API JSON, except maybe feeRateBps/nonce/side/sigType
        # But 'signer' field behavior depends on API version.
        # Let's try sending EXACTLY what the SDK would send.
        
        # 4. Construct the API payload
        # Ensure correct types: Ints for numbers, Strings for amounts/token_id
        # Ensure signer is included for Proxy orders
        
        from eth_utils import to_checksum_address
        
        api_order = {
            "salt": nonce, # Int
            "maker": to_checksum_address(self.funder_address),
            "signer": to_checksum_address(self.signer_address),
            "taker": "0x0000000000000000000000000000000000000000",
            "tokenId": str(message["tokenId"]), # String
            "makerAmount": str(maker_amount), # String
            "takerAmount": str(taker_amount), # String
            "expiration": "0", # String? Try "0"
            "nonce": nonce, # Int
            "feeRateBps": 0, # Int
            "side": message["side"], # Int
            "signatureType": message["signatureType"], # Int
            "signature": signature
        }
        
        return api_order
    
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
        Internal method to place an order via external Node.js script for robustness.
        Overridden to force $1 position size per user request.
        """
        import subprocess
        import os
        import json
        
        # 1. Resolve path to trade.js
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
        script_path = os.path.join(root_dir, "poly-creds", "trade.js")
        
        # 2. Sizing & Aggressive Price Logic
        # We want to spend TARGET_INVESTMENT (~$1.10 USD)
        TARGET_INVESTMENT = 1.1
        
        if side == "BUY":
            # Polymarket API limit is 0.99. 
            # We use a price slightly above the market to ensure fill, but NOT so high that 
            # the locked balance (limit_price * size) exceeds our actual wallet balance.
            market_price = float(price)
            # Safe aggressive price: signal price + 5 cents, capped at 0.99
            safe_aggressive_price = min(0.99, market_price + 0.05)
            
            # Calculate shares based on the actual price we want to pay (the signal price)
            # BUT the total commitment in the CLOB will be shares * safe_aggressive_price
            calculated_size = TARGET_INVESTMENT / market_price
            
            # Final Check: If total commitment > wallet balance ($4), we might still fail.
            # But $1.10 @ 0.25 (market) is ~4 shares. 4 shares @ 0.30 (aggressive) = $1.20. 
            # This is safe for a $4 wallet.
            
            aggressive_price = str(round(safe_aggressive_price, 2))
        else:
            # For SELL, dump the whole position
            calculated_size = size
            aggressive_price = "0.01"

        cmd = [
            "node",
            script_path,
            str(token_id),
            side,
            aggressive_price, 
            str(calculated_size)
        ]
        
        logger.info("live_trader.executing_js_trade", 
                   token_id=token_id, 
                   price=price, 
                   size=calculated_size, 
                   cmd=" ".join(cmd))
        
        try:
            # Execute synchronously (blocking) to ensure order is placed
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            output = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode != 0:
                 logger.error("live_trader.js_execution_error", stderr=stderr, stdout=output)
                 return None
                 
            # Parse output - look for the JSON line
            # The script might output other logs, so we look for the line containing "success":
            lines = output.splitlines()
            json_result = None
            
            for line in reversed(lines):
                if '"success":true' in line or '"success":false' in line:
                    try:
                        json_result = json.loads(line)
                        break
                    except:
                        continue
            
            if not json_result:
                 # Fallback to simple parse
                 try:
                    json_result = json.loads(output)
                 except:
                    logger.error("live_trader.js_output_parse_error", output=output)
                    return None
            
            if json_result.get("success"):
                order_id = json_result.get("orderId")
                logger.info("live_trader.order_placed_successfully", order_id=order_id, details=json_result)
                return order_id
            else:
                logger.error("live_trader.order_placement_failed", details=json_result)
                return None

        except Exception as e:
            logger.exception("live_trader.subprocess_failed", error=str(e))
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
    
    # Get funder address from config (for Polymarket proxy wallets)
    funder_address = getattr(config, 'poly_funder_address', None)
    
    return LiveTrader(
        private_key=config.poly_private_key,
        api_key=config.poly_api_key,
        api_secret=config.poly_api_secret,
        passphrase=config.poly_passphrase,
        funder_address=funder_address,
        signature_type=1,  # Polymarket proxy (most common for polymarket.com accounts)
        host=host
    )
