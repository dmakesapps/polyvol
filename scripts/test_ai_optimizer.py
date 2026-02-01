
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import get_config
from src.core.database import get_database
from src.analysis.ai_optimizer import AIStrategyOptimizer
import structlog

logger = structlog.get_logger()

async def test_optimizer():
    print("=" * 60)
    print("🤖 TESTING AI STRATEGY OPTIMIZER (YOUR AI FRIEND)")
    print("=" * 60)
    
    config = get_config()
    db = await get_database(config.database_path)
    
    # Check API Key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key == "your_openrouter_api_key_here":
        print("❌ ERROR: OPENROUTER_API_KEY is not set in config/.env")
        print("Please add your key from https://openrouter.ai/keys")
        return

    print(f"✅ API Key found (starts with: {api_key[:8]}...)")
    print("📊 Gathering performance data and calling Gemini Flash 3...")
    
    optimizer = AIStrategyOptimizer(db=db, api_key=api_key)
    
    # Run analysis immediately
    insights = await optimizer.run_now()
    
    if not insights or "error" in insights[0]:
        print(f"❌ FAILED: {insights[0].get('error') if insights else 'Unknown error'}")
        return
        
    print(f"\n✨ SUCCESS! Generated {len(insights)} insights:\n")
    
    for i, insight in enumerate(insights, 1):
        priority_emoji = "🔴" if insight.get('priority') == 'high' else "🟡" if insight.get('priority') == 'medium' else "🟢"
        print(f"{i}. {priority_emoji} [{insight.get('category', 'general').upper()}] {insight.get('title')}")
        print(f"   Description: {insight.get('description')}")
        if insight.get('action'):
            print(f"   Action: {insight.get('action')}")
        if insight.get('auto_apply'):
            print(f"   ⚙️ Auto-apply: YES")
        print("-" * 40)

    print("\n✅ AI Friend is working and watching your trades!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_optimizer())
