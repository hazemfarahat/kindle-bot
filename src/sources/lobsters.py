"""Lobsters source implementation."""

from datetime import datetime
from typing import Optional

from dateutil.parser import parse as parse_date

from ..models import Article, SourceConfig, SourceType
from .base import BaseSource


class LobstersSource(BaseSource):
    """Fetches stories from Lobsters JSON feed."""
    
    DEFAULT_URL = "https://lobste.rs/hottest.json"
    
    def __init__(self, config: SourceConfig):
        """Initialize Lobsters source."""
        super().__init__(config)
        self.url = config.url or self.DEFAULT_URL
    
    async def fetch(self) -> list[Article]:
        """Fetch hottest stories from Lobsters.
        
        Returns:
            List of Article objects
        """
        async with self._create_http_client() as client:
            response = await client.get(self.url)
            response.raise_for_status()
            stories = response.json()[:self.max_fetch]
            
            articles = []
            for i, story in enumerate(stories):
                article = self._parse_story(story, position=i)
                if article:
                    articles.append(article)
            
            return articles
    
    def _parse_story(self, story: dict, position: int) -> Optional[Article]:
        """Parse a story from the JSON feed.
        
        Args:
            story: Story data from JSON
            position: Position in the feed
            
        Returns:
            Article object or None
        """
        url = story.get("url")
        if not url:
            # Comments-only posts link to Lobsters discussion
            url = story.get("comments_url", "")
        
        if not url:
            return None
        
        # Parse timestamp
        published = None
        if story.get("created_at"):
            try:
                published = parse_date(story["created_at"])
                # Remove timezone info for consistency
                if published.tzinfo:
                    published = published.replace(tzinfo=None)
            except (ValueError, TypeError):
                pass
        
        # Tags as part of summary
        tags = story.get("tags", [])
        tags_str = ", ".join(tags) if tags else ""
        
        return Article(
            title=story.get("title", "Untitled"),
            url=url,
            source=self.name,
            source_type=SourceType.JSON,
            raw_score=float(story.get("score", 0)),
            position=position,
            author=story.get("submitter_user"),
            published=published,
            summary=f"Score: {story.get('score', 0)} | Tags: {tags_str}" if tags_str else f"Score: {story.get('score', 0)}",
        )
    
    def normalize_score(self, article: Article) -> float:
        """Normalize Lobsters score.
        
        Lobsters scores are typically lower than HN (0-100 range for top stories).
        The weight multiplier in config compensates for this.
        
        Args:
            article: Article to normalize
            
        Returns:
            Normalized score
        """
        return super().normalize_score(article)
