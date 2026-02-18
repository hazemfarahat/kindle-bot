"""Weekly article cache management."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .models import Article


class ArticleCache:
    """Manages article cache for weekly digest aggregation."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files. Defaults to 'cache/'.
        """
        if cache_dir is None:
            cache_dir = "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def save_daily_articles(self, articles: list[Article], date: Optional[datetime] = None) -> str:
        """Save daily articles to cache.
        
        Args:
            articles: Articles to cache
            date: Date for cache file name (defaults to today)
            
        Returns:
            Path to cache file
        """
        if date is None:
            date = datetime.utcnow()
        
        filename = f"articles-{date.strftime('%Y-%m-%d')}.json"
        filepath = self.cache_dir / filename
        
        data = {
            "date": date.isoformat(),
            "article_count": len(articles),
            "articles": [article.to_dict() for article in articles],
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        return str(filepath)
    
    def load_weekly_articles(self, days: int = 7) -> list[Article]:
        """Load articles from the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Combined list of articles
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        all_articles = []
        
        # Find all cache files
        for filepath in sorted(self.cache_dir.glob("articles-*.json")):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                
                # Check date
                file_date = datetime.fromisoformat(data["date"])
                if file_date < cutoff:
                    continue
                
                # Load articles
                for article_data in data.get("articles", []):
                    article = Article.from_dict(article_data)
                    all_articles.append(article)
                    
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Warning: Failed to load cache file {filepath}: {e}")
                continue
        
        return all_articles
    
    def load_from_directory(self, directory: str) -> list[Article]:
        """Load articles from a specific directory.
        
        Used for loading GitHub Action artifacts.
        
        Args:
            directory: Directory containing cache files
            
        Returns:
            List of articles
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        
        all_articles = []
        
        # Look for JSON files in directory and subdirectories
        for filepath in dir_path.rglob("articles-*.json"):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                
                for article_data in data.get("articles", []):
                    article = Article.from_dict(article_data)
                    all_articles.append(article)
                    
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Warning: Failed to load cache file {filepath}: {e}")
                continue
        
        return all_articles
    
    def cleanup_old_files(self, days: int = 14) -> int:
        """Remove cache files older than N days.
        
        Args:
            days: Files older than this will be deleted
            
        Returns:
            Number of files deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = 0
        
        for filepath in self.cache_dir.glob("articles-*.json"):
            try:
                # Extract date from filename
                date_str = filepath.stem.replace("articles-", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff:
                    filepath.unlink()
                    deleted += 1
                    
            except (ValueError, OSError):
                continue
        
        return deleted
    
    def get_cache_stats(self) -> dict:
        """Get statistics about cached articles.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "total_files": 0,
            "total_articles": 0,
            "date_range": {"oldest": None, "newest": None},
            "articles_per_day": {},
        }
        
        for filepath in sorted(self.cache_dir.glob("articles-*.json")):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                
                date_str = data.get("date", "")[:10]
                count = data.get("article_count", 0)
                
                stats["total_files"] += 1
                stats["total_articles"] += count
                stats["articles_per_day"][date_str] = count
                
                if stats["date_range"]["oldest"] is None:
                    stats["date_range"]["oldest"] = date_str
                stats["date_range"]["newest"] = date_str
                
            except (json.JSONDecodeError, KeyError):
                continue
        
        return stats


def save_articles_to_cache(articles: list[Article], cache_dir: Optional[str] = None) -> str:
    """Convenience function to save articles to cache.
    
    Args:
        articles: Articles to cache
        cache_dir: Cache directory
        
    Returns:
        Path to cache file
    """
    cache = ArticleCache(cache_dir)
    return cache.save_daily_articles(articles)


def load_weekly_articles(cache_dir: Optional[str] = None) -> list[Article]:
    """Convenience function to load weekly articles.
    
    Args:
        cache_dir: Cache directory
        
    Returns:
        List of articles
    """
    cache = ArticleCache(cache_dir)
    return cache.load_weekly_articles()
