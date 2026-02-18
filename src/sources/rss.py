"""Generic RSS feed source implementation."""

from datetime import datetime
from typing import Optional
from time import mktime

import feedparser
from dateutil.parser import parse as parse_date

from ..models import Article, SourceConfig, SourceType
from .base import BaseSource


class RSSSource(BaseSource):
    """Fetches articles from RSS feeds."""
    
    def __init__(self, config: SourceConfig):
        """Initialize RSS source."""
        super().__init__(config)
        self.url = config.url
        
        if not self.url:
            raise ValueError(f"RSS source {config.name} requires a URL")
    
    async def fetch(self) -> list[Article]:
        """Fetch articles from RSS feed.
        
        Note: feedparser is synchronous, so we use it directly.
        For true async, we could use httpx to fetch and parse manually.
        
        Returns:
            List of Article objects
        """
        # feedparser handles fetching internally
        feed = feedparser.parse(self.url)
        
        if feed.bozo and not feed.entries:
            # Feed parsing failed completely
            raise ValueError(f"Failed to parse RSS feed: {feed.bozo_exception}")
        
        articles = []
        for i, entry in enumerate(feed.entries[:self.max_fetch]):
            article = self._parse_entry(entry, position=i)
            if article:
                articles.append(article)
        
        return articles
    
    def _parse_entry(self, entry: dict, position: int) -> Optional[Article]:
        """Parse an RSS entry into an Article.
        
        Args:
            entry: feedparser entry
            position: Position in the feed
            
        Returns:
            Article object or None
        """
        # Get URL
        url = entry.get("link")
        if not url:
            return None
        
        # Get title
        title = entry.get("title", "Untitled")
        if not title:
            return None
        
        # Parse published date
        published = None
        if entry.get("published_parsed"):
            try:
                published = datetime.fromtimestamp(mktime(entry.published_parsed))
            except (TypeError, ValueError, OverflowError):
                pass
        elif entry.get("updated_parsed"):
            try:
                published = datetime.fromtimestamp(mktime(entry.updated_parsed))
            except (TypeError, ValueError, OverflowError):
                pass
        elif entry.get("published"):
            try:
                published = parse_date(entry["published"])
                if published.tzinfo:
                    published = published.replace(tzinfo=None)
            except (ValueError, TypeError):
                pass
        
        # Get summary/description
        summary = ""
        if entry.get("summary"):
            # Strip HTML tags for plain text summary
            summary = self._strip_html(entry["summary"])[:500]
        elif entry.get("description"):
            summary = self._strip_html(entry["description"])[:500]
        
        # Get author
        author = None
        if entry.get("author"):
            author = entry["author"]
        elif entry.get("authors"):
            authors = entry.get("authors", [])
            if authors and authors[0].get("name"):
                author = authors[0]["name"]
        
        # RSS feeds don't have scores, so we use position-based scoring
        # Position 0 = highest score (most recent/important)
        raw_score = max(0, 100 - (position * 5))
        
        return Article(
            title=title,
            url=url,
            source=self.name,
            source_type=SourceType.RSS,
            raw_score=float(raw_score),
            position=position,
            author=author,
            published=published,
            summary=summary,
        )
    
    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text.
        
        Args:
            text: HTML text
            
        Returns:
            Plain text
        """
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        clean = clean.replace('&amp;', '&')
        clean = clean.replace('&lt;', '<')
        clean = clean.replace('&gt;', '>')
        clean = clean.replace('&quot;', '"')
        clean = clean.replace('&#39;', "'")
        clean = clean.replace('&nbsp;', ' ')
        # Clean up whitespace
        clean = ' '.join(clean.split())
        return clean.strip()
    
    def normalize_score(self, article: Article) -> float:
        """Normalize RSS score.
        
        RSS feeds are curated by editors, so position matters.
        We assign scores based on position (first = highest).
        
        Args:
            article: Article to normalize
            
        Returns:
            Normalized score
        """
        return super().normalize_score(article)
