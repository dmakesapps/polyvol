#!/usr/bin/env python3
"""
Explore available Polymarket markets.
Use this to discover what markets exist and how they're named.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collection.gamma_client import GammaClient


async def main():
    """Explore available markets."""
    print("=" * 60)
    print("EXPLORING POLYMARKET MARKETS")
    print("=" * 60)
    
    async with GammaClient() as client:
        # Fetch all active markets
        markets = await client.get_markets(active=True, limit=200)
        
        print(f"\nFound {len(markets)} active markets\n")
        
        # Look for crypto-related markets
        crypto_keywords = ["btc", "bitcoin", "eth", "ethereum", "crypto", "sol", "solana"]
        crypto_markets = []
        
        for m in markets:
            question = m.get("question", "").lower()
            if any(kw in question for kw in crypto_keywords):
                crypto_markets.append(m)
        
        print(f"Found {len(crypto_markets)} crypto-related markets:\n")
        print("-" * 60)
        
        for m in crypto_markets[:20]:  # First 20
            question = m.get("question", "")[:80]
            end_date = m.get("endDate", "")[:10]
            
            # Get prices
            tokens = m.get("tokens", [])
            yes_price = "?"
            for t in tokens:
                if t.get("outcome", "").upper() == "YES":
                    yes_price = f"{float(t.get('price', 0)) * 100:.0f}%"
            
            print(f"📊 {question}")
            print(f"   End: {end_date} | YES: {yes_price}")
            print()
        
        if len(crypto_markets) > 20:
            print(f"   ... and {len(crypto_markets) - 20} more\n")
        
        # Look for time-based markets (hourly, daily, etc.)
        print("-" * 60)
        print("\nMARKETS WITH TIME WINDOWS:")
        print("-" * 60)
        
        time_keywords = ["hour", "minute", "day", "today", "tonight", "tomorrow", "week"]
        for m in markets:
            question = m.get("question", "").lower()
            if any(kw in question for kw in time_keywords) and any(kw in question for kw in crypto_keywords):
                end_date = m.get("endDate", "")[:16]
                print(f"⏰ {m.get('question', '')[:70]}")
                print(f"   Ends: {end_date}")
                print()
        
        # Print first 5 market questions to understand format
        print("-" * 60)
        print("\nSAMPLE MARKET QUESTIONS (first 10):")
        print("-" * 60)
        for m in markets[:10]:
            print(f"• {m.get('question', '')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
