"""
Gamma API Client for Polymarket.
Used for market discovery and basic price data.
No authentication required.
"""
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional
import structlog

from ..core.models import Market, PriceUpdate


logger = structlog.get_logger()

# Gamma API endpoints
GAMMA_API_BASE = "https://gamma-api.polymarket.com"


class GammaClient:
    """
    Client for Polymarket's Gamma API.
    Used for discovering markets and fetching prices.
    No API key required.
    """
    
    def __init__(self, timeout: float = 30.0):
        self.base_url = GAMMA_API_BASE
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
        logger.info("gamma_client.connected", base_url=self.base_url)
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("gamma_client.closed")
    
    async def get_markets(
        self,
        active: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """
        Fetch markets from Gamma API.
        
        Args:
            active: Only return active markets
            limit: Max number of markets to return
            offset: Pagination offset
            
        Returns:
            List of market data dictionaries
        """
        params = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": "false"
        }
        
        try:
            response = await self._client.get("/markets", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("gamma_client.get_markets.error", error=str(e))
            return []
    
    async def get_market(self, condition_id: str) -> Optional[dict]:
        """
        Fetch a specific market by condition ID.
        
        Args:
            condition_id: The market's condition ID
            
        Returns:
            Market data or None if not found
        """
        try:
            response = await self._client.get(f"/markets/{condition_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("gamma_client.get_market.error", 
                        condition_id=condition_id, error=str(e))
            return None
    
    async def get_15m_crypto_markets(self) -> list[Market]:
        """
        Fetch the 15-minute crypto up/down markets directly.
        Uses Polymarket's frontend API at /api/crypto/markets.
        
        Returns:
            List of active 15-minute crypto markets
        """
        try:
            # Use the Polymarket frontend API for 15M markets
            # This is separate from the Gamma API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://polymarket.com/api/crypto/markets",
                    params={
                        "_c": "15M",
                        # Note: Removed "_sts": "active" as it returns stale cached data
                        "_l": "20"
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            events = data.get("events", [])
            markets = []
            
            for event in events:
                title = event.get("title", "")
                event_markets = event.get("markets", [])
                
                # Skip closed events
                if event.get("closed", False):
                    continue
                
                # Determine asset from title
                asset = "UNKNOWN"
                title_lower = title.lower()
                if "bitcoin" in title_lower or "btc" in title_lower:
                    asset = "BTC"
                elif "ethereum" in title_lower or "eth" in title_lower:
                    asset = "ETH"
                elif "solana" in title_lower or "sol" in title_lower:
                    asset = "SOL"
                elif "xrp" in title_lower:
                    asset = "XRP"
                
                for m in event_markets:
                    try:
                        market = self._parse_event_market(m, event, asset)
                        # STRICT FILTER: Ignore expired markets (e.g. lagging API returning old ones)
                        if market and market.end_time > datetime.now(timezone.utc):
                            markets.append(market)
                    except Exception as e:
                        logger.warning("gamma_client.parse_event_market.error", error=str(e))
            
            logger.info("gamma_client.get_15m_crypto_markets", found=len(markets))
            return markets
            
        except Exception as e:
            logger.error("gamma_client.get_15m_crypto_markets.error", error=str(e))
            return []
    
    def _parse_event_market(self, market_data: dict, event_data: dict, asset: str) -> Optional[Market]:
        """Parse a market from an event response."""
        try:
            # Extract end time from event
            end_date_str = event_data.get("endDate") or event_data.get("end_date_iso")
            if end_date_str:
                end_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            else:
                # Default to 15 minutes from now if no end time
                end_time = datetime.now(timezone.utc) + timedelta(minutes=15)
            
            # Extract prices - they can be strings like "0.505" or floats
            # Outcomes are typically ["Up", "Down"] - "Up" is like "YES"
            outcome_prices = market_data.get("outcomePrices", [])
            
            # Parse prices safely (they may be strings)
            yes_price = 0.50
            no_price = 0.50
            
            if outcome_prices:
                try:
                    yes_price = float(str(outcome_prices[0]).strip('"'))
                except (ValueError, IndexError):
                    pass
                try:
                    no_price = float(str(outcome_prices[1]).strip('"')) if len(outcome_prices) > 1 else 1 - yes_price
                except (ValueError, IndexError):
                    no_price = 1 - yes_price
            
            # Use bestBid/bestAsk if available (more accurate for trading)
            if market_data.get("bestBid") is not None:
                yes_price = float(market_data["bestBid"])
            if market_data.get("bestAsk") is not None:
                # bestAsk is for buying "Up", adjust no_price accordingly
                pass
            
            # Get volume from event or market level
            volume = float(event_data.get("volume", 0) or 0)
            if not volume:
                volume = float(market_data.get("volume", 0) or 0)
            
            # Get liquidity
            liquidity = float(event_data.get("liquidity", 0) or 0)
            if not liquidity:
                liq_str = str(market_data.get("liquidity", "0") or "0")
                liquidity = float(liq_str)
            
            # Extract CLOB token IDs for real-time orderbook prices
            clob_token_ids = market_data.get("clobTokenIds", [])
            yes_token_id = clob_token_ids[0] if len(clob_token_ids) > 0 else None
            no_token_id = clob_token_ids[1] if len(clob_token_ids) > 1 else None
            
            return Market(
                id=str(market_data.get("id", "")),
                condition_id=market_data.get("conditionId", ""),
                question=event_data.get("title", ""),
                asset=asset,
                end_time=end_time,
                yes_price=yes_price,
                no_price=no_price,
                volume=volume,
                liquidity=liquidity,
                is_active=True,
                yes_token_id=yes_token_id,
                no_token_id=no_token_id
            )
        except Exception as e:
            logger.warning("gamma_client.parse_event_market.error", error=str(e))
            return None

    async def find_crypto_15min_markets(self, asset: str = "BTC") -> list[Market]:
        """
        Find active 15-minute crypto prediction markets.
        
        These markets have questions like:
        - "Bitcoin Up or Down - 15 minute"
        - "Ethereum Up or Down - 15 minute"
        
        Args:
            asset: Crypto asset to search for (BTC, ETH, SOL, XRP, etc.)
            
        Returns:
            List of matching Market objects
        """
        markets = await self.get_markets(active=True, limit=500)
        
        matching = []
        
        # Map common abbreviations to full names
        asset_names = {
            "BTC": ["btc", "bitcoin"],
            "ETH": ["eth", "ethereum"],
            "SOL": ["sol", "solana"],
            "XRP": ["xrp"],
        }
        
        # Get search terms for this asset
        search_terms = asset_names.get(asset.upper(), [asset.lower()])
        
        # Keywords that identify 15-minute markets
        time_keywords = ["15 minute", "15 min", "15min", "15-minute"]
        updown_keywords = ["up or down", "up/down"]
        
        for m in markets:
            question = m.get("question", "").lower()
            
            # Check if this is a 15-minute up/down market for our asset
            has_asset = any(term in question for term in search_terms)
            has_time = any(kw in question for kw in time_keywords)
            has_updown = any(kw in question for kw in updown_keywords)
            
            if has_asset and (has_time or has_updown):
                try:
                    market = self._parse_market(m, asset.upper())
                    if market:
                        matching.append(market)
                        logger.debug("gamma_client.market_found",
                                   question=m.get("question", "")[:50],
                                   yes_price=market.yes_price)
                except Exception as e:
                    logger.warning("gamma_client.parse_market.error",
                                  market_id=m.get("id"), error=str(e))
        
        logger.info("gamma_client.find_crypto_15min_markets",
                   asset=asset, found=len(matching))
        
        return matching
    
    async def get_current_prices(self, markets: list[Market]) -> list[PriceUpdate]:
        """
        Fetch current prices for a list of markets.
        
        Args:
            markets: List of Market objects
            
        Returns:
            List of PriceUpdate objects with current prices
        """
        updates = []
        
        for market in markets:
            try:
                data = await self.get_market(market.condition_id)
                if data:
                    update = self._parse_price_update(data, market.asset)
                    if update:
                        updates.append(update)
            except Exception as e:
                logger.warning("gamma_client.get_prices.error",
                             market_id=market.id, error=str(e))
        
        return updates
    
    def _parse_market(self, data: dict, asset: str) -> Optional[Market]:
        """Parse API response into a Market object."""
        try:
            # Extract end time
            end_date_str = data.get("endDate") or data.get("end_date_iso")
            if end_date_str:
                end_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            else:
                # If no end time, skip this market
                return None
            
            # Extract prices from tokens/outcomes
            yes_price = 0.50
            no_price = 0.50
            
            tokens = data.get("tokens", [])
            for token in tokens:
                outcome = token.get("outcome", "").upper()
                price = float(token.get("price", 0.50))
                if outcome == "YES":
                    yes_price = price
                elif outcome == "NO":
                    no_price = price
            
            # Also check clobTokenIds format
            if "outcomePrices" in data:
                prices = data["outcomePrices"]
                if isinstance(prices, list) and len(prices) >= 2:
                    yes_price = float(prices[0])
                    no_price = float(prices[1])
            
            return Market(
                id=data.get("id", ""),
                condition_id=data.get("conditionId", data.get("condition_id", "")),
                question=data.get("question", ""),
                asset=asset,
                end_time=end_time,
                yes_price=yes_price,
                no_price=no_price,
                volume=float(data.get("volume", 0) or 0),
                liquidity=float(data.get("liquidity", 0) or 0),
                is_active=data.get("active", True)
            )
        except Exception as e:
            logger.warning("gamma_client.parse_market.failed", error=str(e))
            return None
    
    def _parse_price_update(self, data: dict, asset: str) -> Optional[PriceUpdate]:
        """Parse API response into a PriceUpdate object."""
        try:
            # Extract prices
            yes_price = 0.50
            no_price = 0.50
            
            tokens = data.get("tokens", [])
            for token in tokens:
                outcome = token.get("outcome", "").upper()
                price = float(token.get("price", 0.50))
                if outcome == "YES":
                    yes_price = price
                elif outcome == "NO":
                    no_price = price
            
            if "outcomePrices" in data:
                prices = data["outcomePrices"]
                if isinstance(prices, list) and len(prices) >= 2:
                    yes_price = float(prices[0])
                    no_price = float(prices[1])
            
            # Calculate time remaining
            time_remaining = None
            end_date_str = data.get("endDate") or data.get("end_date_iso")
            if end_date_str:
                end_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                time_remaining = (end_time - now).total_seconds()
            
            return PriceUpdate(
                market_id=data.get("id", ""),
                condition_id=data.get("conditionId", data.get("condition_id", "")),
                asset=asset,
                yes_price=yes_price,
                no_price=no_price,
                time_remaining=time_remaining,
                volume=float(data.get("volume", 0) or 0),
                liquidity=float(data.get("liquidity", 0) or 0),
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.warning("gamma_client.parse_price_update.failed", error=str(e))
            return None
