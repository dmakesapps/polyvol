"""
Price Collector - Continuously fetches and stores market prices.
Runs in the background, polling at configured intervals.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
import structlog

from ..core.config import get_config
from ..core.database import Database
from ..core.models import Market, PriceUpdate
from .gamma_client import GammaClient
from .clob_client import CLOBClient


logger = structlog.get_logger()


class PriceCollector:
    """
    Collects prices from Polymarket and stores them in the database.
    Discovers new markets and tracks their prices over time.
    """
    
    def __init__(self, db: Database):
        self.db = db
        self.config = get_config()
        self.gamma_client: Optional[GammaClient] = None
        self.clob_client: Optional[CLOBClient] = None
        
        # Active markets being tracked
        self.markets: dict[str, Market] = {}
        
        # Running state
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the price collector."""
        if self._running:
            return
        
        # Initialize clients
        self.gamma_client = GammaClient()
        self.clob_client = CLOBClient()
        await self.gamma_client.connect()
        await self.clob_client.connect()
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        
        logger.info("price_collector.started",
                   poll_interval=self.config.collection.poll_interval)
    
    async def stop(self) -> None:
        """Stop the price collector."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self.gamma_client:
            await self.gamma_client.close()
        if self.clob_client:
            await self.clob_client.close()
        
        logger.info("price_collector.stopped")
    
    async def _run_loop(self) -> None:
        """Main collection loop."""
        # Initial market discovery
        await self._discover_markets()
        
        while self._running:
            try:
                # Collect prices for all tracked markets
                await self._collect_prices()
                
                # Check for expired markets and discover new ones periodically
                await self._refresh_markets()
                
                # Wait for next poll
                await asyncio.sleep(self.config.collection.poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("price_collector.loop_error", error=str(e))
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _discover_markets(self) -> None:
        """Discover active 15-minute crypto markets."""
        logger.info("price_collector.discovering_markets")
        
        # Try the direct 15M tag endpoint first (most reliable)
        try:
            markets = await self.gamma_client.get_15m_crypto_markets()
            
            now = datetime.now(timezone.utc)
            for market in markets:
                # Only track markets that haven't expired and match our assets
                if market.end_time > now and market.asset in self.config.collection.assets:
                    self.markets[market.condition_id] = market
                    logger.debug("price_collector.market_added",
                               market_id=market.id,
                               asset=market.asset,
                               question=market.question[:50],
                               yes_price=market.yes_price)
            
            if self.markets:
                logger.info("price_collector.markets_discovered",
                           count=len(self.markets),
                           method="tag_id")
                return
                
        except Exception as e:
            logger.warning("price_collector.direct_discover_failed", error=str(e))
        
        # Fall back to keyword search method
        for asset in self.config.collection.assets:
            try:
                markets = await self.gamma_client.find_crypto_15min_markets(asset)
                
                for market in markets:
                    now = datetime.now(timezone.utc)
                    if market.end_time > now:
                        self.markets[market.condition_id] = market
                        logger.debug("price_collector.market_added",
                                   market_id=market.id,
                                   asset=asset,
                                   end_time=market.end_time.isoformat())
                
            except Exception as e:
                logger.error("price_collector.discover_error",
                           asset=asset, error=str(e))
        
        logger.info("price_collector.markets_discovered",
                   count=len(self.markets),
                   method="keyword_search")
    
    async def _collect_prices(self) -> None:
        """Collect current prices for all tracked markets.
        
        Uses the frontend API prices (AMM/last trade) since CLOB orderbooks
        for 15-min markets are extremely illiquid with ~99% spreads.
        """
        if not self.markets:
            await self._discover_markets()
            return
        
        now = datetime.now(timezone.utc)
        expired = []
        
        # Fetch fresh AMM prices from frontend API (single request)
        try:
            fresh_markets = await self.gamma_client.get_15m_crypto_markets()
            fresh_by_id = {m.condition_id: m for m in fresh_markets}
        except Exception as e:
            logger.error("price_collector.api_error", error=str(e))
            fresh_by_id = {}
        
        for condition_id, market in self.markets.items():
            try:
                # Check if market has expired
                if market.end_time <= now:
                    expired.append(condition_id)
                    continue
                
                # Calculate time remaining
                time_remaining = (market.end_time - now).total_seconds()
                
                # Get prices from fresh API data (AMM prices)
                yes_price = market.yes_price
                no_price = market.no_price
                
                if condition_id in fresh_by_id:
                    fresh = fresh_by_id[condition_id]
                    yes_price = fresh.yes_price
                    no_price = fresh.no_price
                
                # Update market object with latest prices from API
                market.yes_price = yes_price
                market.no_price = no_price

                # OVERRIDE with CLOB Bid/Ask Data (Real-time accuracy)
                # Fetch order book data to catch the real spread
                yes_bid = None
                yes_ask = None
                no_bid = None
                no_ask = None
                
                if market.yes_token_id and market.no_token_id:
                    clob_data = await self.clob_client.get_best_bid_ask(
                        market.yes_token_id, 
                        market.no_token_id
                    )
                    
                    if clob_data:
                        yes_bid = clob_data.get("yes_bid")
                        yes_ask = clob_data.get("yes_ask")
                        no_bid = clob_data.get("no_bid")
                        no_ask = clob_data.get("no_ask")
                        
                        # Store EXECUTION prices on the market object (Critical for paper trading)
                        market.yes_bid = yes_bid
                        market.yes_ask = yes_ask
                        market.no_bid = no_bid
                        market.no_ask = no_ask
                        
                        # Update "display" prices to Midpoint or Last Trade if available
                        # But keep the Bid/Ask separate for execution
                        if clob_data.get("yes_mid"):
                            yes_price = clob_data["yes_mid"]
                        if clob_data.get("no_mid"):
                            no_price = clob_data["no_mid"]
                        elif no_ask and no_bid:
                             no_price = (no_ask + no_bid) / 2

                # Create price update
                price_update = PriceUpdate(
                    market_id=market.id,
                    condition_id=market.condition_id,
                    asset=market.asset,
                    yes_price=yes_price,
                    no_price=no_price,
                    yes_bid=yes_bid,
                    yes_ask=yes_ask,
                    no_bid=no_bid,
                    no_ask=no_ask,
                    time_remaining=time_remaining,
                    volume=market.volume,
                    liquidity=market.liquidity,
                    timestamp=now
                )
                
                # Save to database
                await self.db.save_price(price_update)
                
                logger.debug("price_collector.price_updated",
                           asset=market.asset,
                           yes=f"{yes_price:.1%}",
                           no=f"{no_price:.1%}",
                           time_remaining=int(time_remaining))
                
            except Exception as e:
                logger.error("price_collector.collect_error", 
                           asset=market.asset, error=str(e))
        
        # Remove expired markets
        for condition_id in expired:
            del self.markets[condition_id]
            logger.info("price_collector.market_expired",
                       condition_id=condition_id)
    
    async def _refresh_markets(self) -> None:
        """
        Periodically refresh market list.
        Removes expired markets and discovers new ones.
        """
        now = datetime.now(timezone.utc)
        
        # Remove expired markets
        expired = [
            cid for cid, m in self.markets.items()
            if m.end_time <= now
        ]
        for cid in expired:
            del self.markets[cid]
        
        # If few markets remain, discover new ones
        if len(self.markets) < 3:
            await self._discover_markets()
    
    def get_current_markets(self) -> list[Market]:
        """Get all currently tracked markets."""
        return list(self.markets.values())
    
    def get_market_price(self, condition_id: str) -> Optional[PriceUpdate]:
        """Get the latest price for a market."""
        market = self.markets.get(condition_id)
        if not market:
            return None
        
        now = datetime.now(timezone.utc)
        time_remaining = (market.end_time - now).total_seconds()
        
        return PriceUpdate(
            market_id=market.id,
            condition_id=market.condition_id,
            asset=market.asset,
            yes_price=market.yes_price,
            no_price=market.no_price,
            yes_bid=market.yes_bid,
            yes_ask=market.yes_ask,
            no_bid=market.no_bid,
            no_ask=market.no_ask,
            time_remaining=time_remaining,
            volume=market.volume,
            liquidity=market.liquidity,
            timestamp=now
        )
