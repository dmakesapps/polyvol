import asyncio
import sys
from src.collection.clob_client import CLOBClient
from src.collection.gamma_client import GammaClient

async def check_spreads():
    print("=" * 60)
    print("🕵️  REAL-TIME SPREAD AUDIT")
    print("=" * 60)
    print(f"{'Asset':<6} | {'Bid (Sell Here)':<15} | {'Ask (Buy Here)':<15} | {'Spread':<10} | {'Last Traded':<12}")
    print("-" * 60)

    async with CLOBClient() as clob:
        async with GammaClient() as gamma:
            # 1. Get active 15m markets
            markets = await gamma.get_15m_crypto_markets()
            
            for m in markets[:5]: # Check top 5 active markets
                # We usually trade 'NO' (Short)
                # So we BUY at NO_ASK and SELL at NO_BID
                
                # Get Order Book for NO token
                no_token = m.no_token_id
                if not no_token:
                    print(f"{m.asset:<6} | {'--':<15} | {'--':<15} | {'No Token ID':<10} | {'--':<12}")
                    continue

                book = await clob.get_order_book(no_token)
                last_price = await clob.get_last_price(no_token)
                
                bid = 0.0
                ask = 0.0
                
                if book and book.get("bids"):
                    bid = float(book["bids"][0]["price"])
                
                if book and book.get("asks"):
                    ask = float(book["asks"][0]["price"])
                
                spread = ask - bid
                spread_pct = (spread / ask) * 100 if ask > 0 else 0
                
                # Color code
                spread_str = f"{spread:.3f} ({spread_pct:.1f}%)"
                last_str = f"{last_price:.3f}" if last_price else "—"
                
                print(f"{m.asset:<6} | {bid:<15.3f} | {ask:<15.3f} | {spread_str:<10} | {last_str:<12}")

    print("=" * 60)
    print("NOTE: If 'Last Traded' is closer to Bid or Ask, it shows")
    print("which side is being aggressive. Large spreads make")
    print("profit harder than the simulation shows.")

if __name__ == "__main__":
    asyncio.run(check_spreads())
