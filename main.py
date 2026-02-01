"""
Polymarket Volatility Trading Bot
Main entry point - runs 24/7 collecting data and paper trading.
"""
import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path
import structlog
import logging

# Configure stdlib logging
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
)

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(colors=True)
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("POLYMARKET VOLATILITY TRADING BOT")
    logger.info("=" * 60)
    logger.info("Starting up...")
    
    # Import here to avoid circular imports
    from src.core.config import get_config
    from src.core.database import get_database
    from src.collection.price_collector import PriceCollector
    from src.strategies.runner import StrategyRunner
    from src.analysis.reporter import Reporter
    
    # Load configuration
    config = get_config()
    logger.info(
        "config.loaded",
        mode=config.mode,
        strategies=len(config.strategies),
        assets=config.collection.assets
    )
    
    # Ensure data directory exists
    Path(config.database_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize database
    db = await get_database(config.database_path)
    logger.info("database.connected", path=config.database_path)
    
    # Initialize components
    price_collector = PriceCollector(db)
    strategy_runner = StrategyRunner(db, price_collector)
    reporter = Reporter(db)
    
    # Handle shutdown signals
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig):
        logger.info("shutdown.signal_received", signal=sig)
        shutdown_event.set()
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_event_loop().add_signal_handler(
            sig, lambda s=sig: signal_handler(s)
        )
    
    try:
        # Start components
        await price_collector.start()
        await strategy_runner.start()
        
        logger.info("=" * 60)
        logger.info("BOT IS NOW RUNNING")
        logger.info("=" * 60)
        logger.info("Watching for 15-minute crypto markets...")
        logger.info("Paper trading with 18 strategies...")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        # Main loop - run until shutdown
        last_report = datetime.utcnow()
        last_status = datetime.utcnow()
        report_interval = config.analysis.interval  # seconds
        status_interval = 30  # Show prices every 30 sec
        
        while not shutdown_event.is_set():
            try:
                # Wait a bit
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                pass
            
            now = datetime.utcnow()
            
            # Periodic status (every 30 sec)
            if (now - last_status).total_seconds() >= status_interval:
                markets = price_collector.get_current_markets()
                positions = strategy_runner.get_open_positions()
                
                logger.info("-" * 50)
                logger.info("MARKET PRICES:")
                for m in markets:
                    # Check for potential entries
                    signals = []
                    if m.yes_price <= 0.20:
                        signals.append("📈 BUY YES")
                    if m.no_price <= 0.20:
                        signals.append("📉 BUY NO")
                    
                    signal_str = f" [{', '.join(signals)}]" if signals else ""
                    logger.info(f"  {m.asset:4} | Up: {m.yes_price:.1%} | Down: {m.no_price:.1%}{signal_str}")
                
                if positions:
                    logger.info("OPEN POSITIONS:")
                    for p in positions:
                        logger.info(f"  {p.strategy_id}: {p.side.value} {p.asset} @ {p.entry_price:.1%}")
                else:
                    logger.info("No open positions - waiting for extreme prices...")
                
                logger.info("-" * 50)
                last_status = now
            
            # Full report (hourly)
            if (now - last_report).total_seconds() >= report_interval:
                await reporter.print_quick_status()
                last_report = now
        
    except Exception as e:
        logger.error("main.error", error=str(e))
        raise
    finally:
        # Shutdown
        logger.info("shutdown.starting")
        await strategy_runner.stop()
        await price_collector.stop()
        await db.close()
        logger.info("shutdown.complete")


def run():
    """Entry point for running the bot."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    run()
