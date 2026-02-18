"""Dev.to source implementation."""

from datetime import datetime
from typing import Optional

from dateutil.parser import parse as parse_date

from ..models import Article, SourceConfig, SourceType
from .base import BaseSource


class DevToSource(BaseSource):
    """Fetches top articles from Dev.to API."""
    
    DEFAULT_URL = "https://dev.to/api/articles"
    
    def __init__(self, config: SourceConfig):
        """Initialize Dev.to source."""
        super().__init__(config)
        self.url = config.url or self.DEFAULT_URL
    
    async def fetch(self) -> list[Article]:
        """Fetch top articles from Dev.to.
        
        Returns:
            List of Article objects
        """
        async with self._create_http_client() as client:
            # Fetch top articles (sorted by popularity by default)
            params = {
                "per_page": self.max_fetch,
                "top": 1,  # Top articles from the past day
            }
            response = await client.get(self.url, params=params)
            response.raise_for_status()
            articles_data = response.json()
            
            articles = []
            for i, article_data in enumerate(articles_data):
                article = self._parse_article(article_data, position=i)
                if article:
                    articles.append(article)
            
            return articles
    
    def _parse_article(self, data: dict, position: int) -> Optional[Article]:
        """Parse an article from the API response.
        
        Args:
            data: Article data from API
            position: Position in the results
            
        Returns:
            Article object or None
        """
        url = data.get("url")
        if not url:
            return None
        
        # Parse timestamp
        published = None
        if data.get("published_at"):
            try:
                published = parse_date(data["published_at"])
                if published.tzinfo:
                    published = published.replace(tzinfo=None)
            except (ValueError, TypeError):
                pass
        
        # Calculate score from reactions and comments
        reactions = data.get("public_reactions_count", 0) or data.get("positive_reactions_count", 0)
        comments = data.get("comments_count", 0)
        # Weight reactions more than comments
        raw_score = reactions + (comments * 0.5)
        
        # Tags
        tags = data.get("tag_list", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        tags_str = ", ".join(tags[:5]) if tags else ""
        
        return Article(
            title=data.get("title", "Untitled"),
            url=url,
            source=self.name,
            source_type=SourceType.API,
            raw_score=float(raw_score),
            position=position,
            author=data.get("user", {}).get("username"),
            published=published,
            summary=data.get("description", "") or f"Reactions: {reactions} | Tags: {tags_str}",
        )
    
    def normalize_score(self, article: Article) -> float:
        """Normalize Dev.to score.
        
        Dev.to articles can get very high reaction counts (1000+).
        The weight in config should be lower to compensate.
        
        Args:
            article: Article to normalize
            
        Returns:
            Normalized score
        """
        return super().normalize_score(article)
