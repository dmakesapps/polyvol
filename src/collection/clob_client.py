"""
CLOB (Central Limit Order Book) API Client for Polymarket.
Used for order book data and more accurate pricing.
Read operations require no authentication.
"""
import httpx
from datetime import datetime, timezone
from typing import Optional
import structlog

from ..core.models import PriceUpdate


logger = structlog.get_logger()

# CLOB API endpoints
CLOB_API_BASE = "https://clob.polymarket.com"


class CLOBClient:
    """
    Client for Polymarket's CLOB API.
    Provides order book depth and accurate bid/ask prices.
    Read operations require no API key.
    """
    
    def __init__(self, timeout: float = 30.0):
        self.base_url = CLOB_API_BASE
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self) -> None:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Accept": "application/json"}
        )
        logger.info("clob_client.connected", base_url=self.base_url)
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("clob_client.closed")
    
    async def get_order_book(self, token_id: str) -> Optional[dict]:
        """
        Get the order book for a token.
        
        Args:
            token_id: The token ID to get order book for
            
        Returns:
            Order book data with bids and asks
        """
        try:
            response = await self._client.get(
                "/book",
                params={"token_id": token_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("clob_client.get_order_book.error",
                        token_id=token_id, error=str(e))
            return None
    
    async def get_price(self, token_id: str) -> Optional[dict]:
        """
        Get the current price for a token.
        
        Args:
            token_id: The token ID
            
        Returns:
            Price data including bid, ask, and mid
        """
        try:
            response = await self._client.get(
                "/price",
                params={"token_id": token_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("clob_client.get_price.error",
                        token_id=token_id, error=str(e))
            return None
    
    async def get_midpoint(self, token_id: str) -> Optional[float]:
        """
        Get the midpoint price for a token.
        
        Args:
            token_id: The token ID
            
        Returns:
            Midpoint price or None
        """
        try:
            response = await self._client.get(
                "/midpoint",
                params={"token_id": token_id}
            )
            response.raise_for_status()
            data = response.json()
            return float(data.get("mid", 0))
        except httpx.HTTPError as e:
            logger.error("clob_client.get_midpoint.error",
                        token_id=token_id, error=str(e))
            return None
    
    async def get_spread(self, token_id: str) -> Optional[dict]:
        """
        Get the bid-ask spread for a token.
        
        Args:
            token_id: The token ID
            
        Returns:
            Spread data including bid, ask, and spread percentage
        """
        try:
            response = await self._client.get(
                "/spread",
                params={"token_id": token_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("clob_client.get_spread.error",
                        token_id=token_id, error=str(e))
            return None
    
    async def get_markets(self, next_cursor: str = "") -> Optional[dict]:
        """
        Get list of markets from CLOB.
        
        Args:
            next_cursor: Pagination cursor
            
        Returns:
            Markets data with pagination info
        """
        try:
            params = {}
            if next_cursor:
                params["next_cursor"] = next_cursor
            
            response = await self._client.get("/markets", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("clob_client.get_markets.error", error=str(e))
            return None
    
    async def get_market(self, condition_id: str) -> Optional[dict]:
        """
        Get a specific market by condition ID.
        
        Args:
            condition_id: The condition ID
            
        Returns:
            Market data
        """
        try:
            response = await self._client.get(f"/markets/{condition_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("clob_client.get_market.error",
                        condition_id=condition_id, error=str(e))
            return None
    
    async def get_best_bid_ask(
        self, 
        yes_token_id: str,
        no_token_id: str
    ) -> Optional[dict]:
        """
        Get the best bid and ask for both YES and NO tokens.
        
        Args:
            yes_token_id: Token ID for YES outcome
            no_token_id: Token ID for NO outcome
            
        Returns:
            Dict with yes_bid, yes_ask, no_bid, no_ask
        """
        result = {
            "yes_bid": None,
            "yes_ask": None,
            "no_bid": None,
            "no_ask": None,
            "yes_mid": None,
            "no_mid": None
        }
        
        # Get YES order book
        yes_book = await self.get_order_book(yes_token_id)
        if yes_book:
            bids = yes_book.get("bids", [])
            asks = yes_book.get("asks", [])
            if bids:
                result["yes_bid"] = float(bids[0].get("price", 0))
            if asks:
                result["yes_ask"] = float(asks[0].get("price", 0))
            if result["yes_bid"] and result["yes_ask"]:
                result["yes_mid"] = (result["yes_bid"] + result["yes_ask"]) / 2
        
        # Get NO order book
        no_book = await self.get_order_book(no_token_id)
        if no_book:
            bids = no_book.get("bids", [])
            asks = no_book.get("asks", [])
            if bids:
                result["no_bid"] = float(bids[0].get("price", 0))
            if asks:
                result["no_ask"] = float(asks[0].get("price", 0))
            if result["no_bid"] and result["no_ask"]:
                result["no_mid"] = (result["no_bid"] + result["no_ask"]) / 2
        
        return result
    
    async def get_recent_trades(
        self, 
        token_id: str,
        limit: int = 50
    ) -> list[dict]:
        """
        Get recent trades for a token.
        
        Args:
            token_id: The token ID
            limit: Max number of trades to return
            
        Returns:
            List of recent trades
        """
        try:
            response = await self._client.get(
                "/trades",
                params={"token_id": token_id, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("clob_client.get_recent_trades.error",
                        token_id=token_id, error=str(e))
            return []

    async def get_last_price(self, token_id: str) -> Optional[float]:
        """Get the last trade price (ticker) for a token."""
        try:
            # Quick fetch for price
            if not self._client:
                return None
                
            response = await self._client.get(
                "/price",
                params={"token_id": token_id, "side": "BUY"}
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get("price", 0))
            return None
        except Exception:
            return None
