#!/usr/bin/env python3
"""
Try to find the 15-minute crypto markets by exploring different API patterns.
"""
import asyncio
import httpx


async def main():
    """Try various API endpoints that might serve 15M markets."""
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        print("=" * 60)
        print("SEARCHING FOR 15M CRYPTO API ENDPOINT")
        print("=" * 60)
        
        # Possible base URLs
        base_urls = [
            "https://gamma-api.polymarket.com",
            "https://clob.polymarket.com", 
            "https://api.polymarket.com",
            "https://strapi-matic.poly.market",
        ]
        
        # Possible endpoints for 15-minute markets
        endpoints = [
            "/events?slug=15-min-crypto",
            "/events?slug=crypto-15-min",
            "/events?slug=bitcoin-up-or-down-15-minute",
            "/events?tag=15-minute",
            "/events?category=15-min",
            "/markets?tag=15-min",
            "/markets?tag=15-minute",
            "/markets?slug=bitcoin-up-or-down-15-minute",
            "/markets?event=15-min-crypto",
            "/events?active=true",
        ]
        
        found_endpoints = []
        
        for base_url in base_urls:
            print(f"\n--- Checking {base_url} ---")
            
            for endpoint in endpoints:
                try:
                    url = f"{base_url}{endpoint}"
                    resp = await client.get(url)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        count = len(data) if isinstance(data, list) else "dict"
                        
                        # Check if any results contain 15 minute markets
                        has_15min = False
                        if isinstance(data, list):
                            for item in data:
                                text = str(item).lower()
                                if "15 minute" in text or "up or down" in text:
                                    has_15min = True
                                    break
                        
                        status = "✅ FOUND 15MIN!" if has_15min else f"({count} items)"
                        if has_15min:
                            found_endpoints.append(url)
                            print(f"  {endpoint}: {status}")
                            # Print first matching item
                            for item in data[:3]:
                                q = item.get("question", item.get("title", item.get("description", "")))
                                if "15 minute" in str(q).lower() or "up or down" in str(q).lower():
                                    print(f"    → {q[:60]}")
                        
                except httpx.HTTPError:
                    pass
                except Exception as e:
                    pass
        
        # Check specific event slugs that might exist
        print("\n--- Checking specific event slugs ---")
        event_slugs = [
            "bitcoin-up-or-down-15-minute",
            "ethereum-up-or-down-15-minute", 
            "solana-up-or-down-15-minute",
            "xrp-up-or-down-15-minute",
            "15-min-crypto",
            "crypto-15m",
        ]
        
        for slug in event_slugs:
            try:
                resp = await client.get(f"https://gamma-api.polymarket.com/events/{slug}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"  ✅ Found: {slug}")
                    if isinstance(data, dict):
                        print(f"     Title: {data.get('title', 'N/A')[:50]}")
                        print(f"     Markets: {len(data.get('markets', []))}")
            except:
                pass
        
        # Try searching with text query
        print("\n--- Text search ---")
        try:
            resp = await client.get("https://gamma-api.polymarket.com/markets", params={
                "limit": 100,
                "text_search": "15 minute"
            })
            if resp.status_code == 200:
                data = resp.json()
                print(f"  text_search='15 minute': {len(data)} results")
                for m in data[:5]:
                    print(f"    - {m.get('question', '')[:60]}")
        except Exception as e:
            print(f"  Error: {e}")
        
        print("\n" + "=" * 60)
        if found_endpoints:
            print("FOUND THESE WORKING ENDPOINTS:")
            for ep in found_endpoints:
                print(f"  ✅ {ep}")
        else:
            print("No 15-minute market endpoints found via API.")
            print("\nThe 15-minute markets may be:")
            print("  1. Using a WebSocket-only feed")
            print("  2. Served by a different internal API")
            print("  3. Only accessible after authentication")


if __name__ == "__main__":
    asyncio.run(main())
