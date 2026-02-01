#!/usr/bin/env python3
"""
Run analysis and generate performance report.
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import get_database
from src.core.config import get_config
from src.analysis.reporter import Reporter


async def main(hours: int = None, json_output: bool = False):
    """Run analysis."""
    config = get_config()
    db = await get_database(config.database_path)
    reporter = Reporter(db)
    
    if json_output:
        import json
        report = await reporter.generate_json_report(hours)
        print(json.dumps(report, indent=2, default=str))
    else:
        report = await reporter.generate_summary(hours)
        print(report)
    
    await db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate performance report")
    parser.add_argument(
        "--hours", "-H", type=int, default=None,
        help="Time window in hours (default: all time)"
    )
    parser.add_argument(
        "--json", "-j", action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    asyncio.run(main(args.hours, args.json))
