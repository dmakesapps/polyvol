
import asyncio
import sys
import os

# Add CWD to path
sys.path.append(os.getcwd())

from src.core.config import get_config
from src.collection.live_trader import create_live_trader
from src.collection.gamma_client import GammaClient
from src.core.models import Side

async def force_sell():
    config = get_config()
    print(f"Loaded config mode: {config.mode}")
    
    # Force LIVE mode even if config says paper, just for this test
    # (Though user seems to be in live mode already)
    config.mode = "live"
    
    trader = create_live_trader(config)
    if not trader:
        print("Failed to create LiveTrader. Check credentials.")
        return

    gamma = GammaClient()
    
    # Target Trade: ETH NO (Trade ID 284)
    # Uses Market ID for lookup, not condition ID
    market_id = "1305124"
    side = Side.NO
    shares_to_sell = 1.0  # Sell 1 share as a test
    
    print(f"Connecting to Trader...")
    await trader.connect()
    
    print(f"Connecting to Gamma API...")
    await gamma.connect()
    
    try:
        print(f"Fetching market details for ID: {market_id}")
        market_data = await gamma.get_market(market_id)
        
        if not market_data:
            print("Market not found via Gamma API!")
            return

        print("Market Data Keys:", market_data.keys())
        
import json

        # Extract Token IDs
        clob_token_ids = market_data.get("clobTokenIds", [])
        print(f"Raw CLOB Token IDs: {clob_token_ids} (Type: {type(clob_token_ids)})")
        
        if isinstance(clob_token_ids, str):
            try:
                clob_token_ids = json.loads(clob_token_ids)
            except json.JSONDecodeError:
                print(f"Failed to parse CLOB Token IDs string: {clob_token_ids}")
                return

        if not clob_token_ids or len(clob_token_ids) < 2:
            print(f"No CLOB Token IDs found in market data: {clob_token_ids}")
            return
            
        # [YES_TOKEN, NO_TOKEN]
        token_id = clob_token_ids[1] if side == Side.NO else clob_token_ids[0]
        # Strip generic quotes if present
        token_id = str(token_id).replace('"', '').replace("'", "")
        print(f"Found Token ID: {token_id}")
        
        print(f"Attempting to SELL {shares_to_sell} shares of {side.value}...")
        
        # Use aggressive pricing (Limit Sell @ 0.01) - same as bot logic
        # But LiveTrader methods are buy_yes/buy_no/sell_yes/sell_no
        
        order_id = None
        if side == Side.YES:
            order_id = await trader.sell_yes(token_id, price=0.01, size=shares_to_sell)
        else:
            order_id = await trader.sell_no(token_id, price=0.01, size=shares_to_sell)
            
        if order_id:
            print(f"SUCCESS! Order placed. ID: {order_id}")
        else:
            print("FAILED to place order.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await trader.close()
        await gamma.close()

if __name__ == "__main__":
    asyncio.run(force_sell())
