#!/usr/bin/env python3
"""Test web builder with cached article data."""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.web_builder import WebBuilder
from src.models import Article, SourceError, SourceType


def test_web_builder():
    """Test web builder with cached articles."""
    # Load cached articles
    cache_path = Path("cache/articles-2026-02-23.json")
    
    if not cache_path.exists():
        print(f"Error: Cache file not found: {cache_path}")
        return False
    
    print(f"Loading articles from {cache_path}...")
    
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert to Article objects
    articles = [Article.from_dict(a) for a in data['articles']]
    
    print(f"Loaded {len(articles)} articles")
    
    # Create some test errors
    errors = [
        SourceError(
            source="test_source",
            error="This is a test error",
            timestamp=datetime.now(),
        )
    ]
    
    # Build web pages
    print("\nBuilding web pages...")
    builder = WebBuilder()
    
    output_dir = builder.build(
        articles=articles,
        digest_type="daily",
        errors=errors,
        output_dir="docs",
        keep_days=7,
        summary="**Today's Tech Highlights**\n\nE-paper dashboards and family tech. Timeframe showcases a decade-long journey to build the perfect family dashboard using e-paper displays.\n\n**Google AI restrictions without warning.** Users report account restrictions when using third-party tools like OpenClaw with Google AI Pro/Ultra subscriptions.",
    )
    
    print(f"\n✓ Web pages generated in: {output_dir}")
    print(f"\nGenerated files:")
    
    # List generated files
    for item in sorted(output_dir.rglob("*")):
        if item.is_file():
            size = item.stat().st_size
            rel_path = item.relative_to(output_dir)
            print(f"  - {rel_path} ({size:,} bytes)")
    
    return True


if __name__ == "__main__":
    success = test_web_builder()
    sys.exit(0 if success else 1)
