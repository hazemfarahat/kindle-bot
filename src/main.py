"""Main entry point for Kindle News Digest."""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .aggregator import Aggregator
from .cache import ArticleCache
from .config import get_config
from .epub_builder import build_epub
from .extractor import extract_content
from .emailer import send_epub_to_kindle
from .models import Article, SourceError


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_status(icon: str, message: str) -> None:
    """Print a status message."""
    print(f"  {icon} {message}")


async def run_digest(
    digest_type: str,
    article_count: int,
    send_email: bool = True,
    output_path: Optional[str] = None,
    cache_dir: Optional[str] = None,
) -> tuple[str, list[SourceError]]:
    """Run the digest generation pipeline.
    
    Args:
        digest_type: Type of digest ('daily', 'weekly', 'run-once')
        article_count: Number of articles to include
        send_email: Whether to send email to Kindle
        output_path: Custom output path for EPUB
        cache_dir: Cache directory for weekly digest
        
    Returns:
        Tuple of (EPUB path, errors)
    """
    config = get_config()
    errors: list[SourceError] = []
    
    # Step 1: Fetch and aggregate articles
    print_status("📡", "Fetching sources...")
    
    if digest_type == "weekly" and cache_dir:
        # Load from cache for weekly
        cache = ArticleCache()
        articles = cache.load_from_directory(cache_dir)
        
        if not articles:
            # Fallback: fetch fresh
            print_status("⚠️", "No cached articles found, fetching fresh...")
            aggregator = Aggregator()
            articles, errors = await aggregator.aggregate(article_count)
        else:
            # Re-deduplicate and rank cached articles
            aggregator = Aggregator()
            articles = aggregator.deduplicate(articles)
            articles = aggregator.rank(articles, article_count)
            print_status("✓", f"Loaded {len(articles)} articles from cache")
    else:
        # Fetch fresh for daily/run-once
        aggregator = Aggregator()
        articles, errors = await aggregator.aggregate(article_count)
    
    # Print source results
    sources_by_name: dict[str, int] = {}
    for article in articles:
        sources_by_name[article.source] = sources_by_name.get(article.source, 0) + 1
    
    for source, count in sources_by_name.items():
        print_status("  ✓", f"{source}: {count} articles")
    
    for error in errors:
        print_status("  ✗", f"{error.source}: {error.error}")
    
    if not articles:
        raise RuntimeError("No articles fetched from any source")
    
    print_status("✓", f"Aggregated {len(articles)} articles")
    
    # Step 2: Extract content
    print_status("📝", "Extracting content...")
    
    articles = await extract_content(articles)
    
    full_content_count = sum(1 for a in articles if not a.is_summary_only)
    summary_count = sum(1 for a in articles if a.is_summary_only)
    
    print_status("✓", f"Full articles: {full_content_count}, Summaries: {summary_count}")
    
    # Step 3: Generate EPUB
    print_status("📚", "Generating EPUB...")
    
    epub_path = build_epub(
        articles=articles,
        digest_type=digest_type,
        errors=errors if errors else None,
        output_path=output_path,
    )
    
    epub_size = Path(epub_path).stat().st_size / 1024 / 1024  # MB
    print_status("✓", f"Generated: {epub_path} ({epub_size:.1f} MB)")
    
    # Step 4: Save to cache (for daily runs)
    if digest_type in ("daily", "run-once"):
        cache = ArticleCache()
        cache_path = cache.save_daily_articles(articles)
        print_status("💾", f"Cached articles: {cache_path}")
    
    # Step 5: Send email
    if send_email:
        print_status("📧", "Sending to Kindle...")
        
        try:
            send_epub_to_kindle(epub_path, digest_type=digest_type)
            print_status("✓", f"Sent to {config.kindle_email}")
        except Exception as e:
            errors.append(SourceError(
                source="emailer",
                error=str(e),
                timestamp=datetime.utcnow(),
            ))
            print_status("✗", f"Email failed: {e}")
    else:
        print_status("⏭️", "Email skipped (--no-email)")
    
    return epub_path, errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Kindle Tech News Digest - Daily tech news delivered to your Kindle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daily scheduled digest
  python -m src.main --type daily
  
  # Weekly scheduled digest
  python -m src.main --type weekly --cache-dir cache/
  
  # Run once immediately
  python -m src.main --run-once
  
  # Run once with custom settings
  python -m src.main --run-once --articles 15 --no-email
  
  # Run once with custom output
  python -m src.main --run-once --output ~/Desktop/digest.epub
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--type",
        choices=["daily", "weekly"],
        help="Scheduled digest type"
    )
    mode_group.add_argument(
        "--run-once",
        action="store_true",
        help="Run immediately, fetch and send right away"
    )
    
    # Options
    parser.add_argument(
        "--articles", "-n",
        type=int,
        default=None,
        help="Number of articles to include (default: from config)"
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Generate EPUB but don't send to Kindle"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Custom output path for EPUB file"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        help="Directory containing article caches (for weekly digest)"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config.yaml file"
    )
    
    args = parser.parse_args()
    
    # Load config
    if args.config:
        from .config import reload_config
        reload_config(args.config)
    
    config = get_config()
    
    # Determine digest type and article count
    if args.run_once:
        digest_type = "run-once"
        article_count = args.articles or config.daily_article_count
    elif args.type == "weekly":
        digest_type = "weekly"
        article_count = args.articles or config.weekly_article_count
    else:
        digest_type = "daily"
        article_count = args.articles or config.daily_article_count
    
    # Print header
    print_header(f"Kindle News Digest - {digest_type.title()}")
    print(f"  Articles: {article_count}")
    print(f"  Email: {'Yes' if not args.no_email else 'No'}")
    if args.output:
        print(f"  Output: {args.output}")
    print()
    
    # Run async pipeline
    try:
        epub_path, errors = asyncio.run(run_digest(
            digest_type=digest_type,
            article_count=article_count,
            send_email=not args.no_email,
            output_path=args.output,
            cache_dir=args.cache_dir,
        ))
        
        # Print summary
        print_header("Complete!")
        print_status("📄", f"EPUB: {epub_path}")
        
        if errors:
            print()
            print_status("⚠️", f"{len(errors)} source(s) had issues:")
            for error in errors:
                print_status("  •", f"{error.source}: {error.error}")
        
        print()
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print_header("Error")
        print_status("❌", str(e))
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
