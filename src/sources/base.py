"""Base class for news sources."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import httpx

from ..models import Article, SourceConfig


class BaseSource(ABC):
    """Abstract base class for all news sources."""
    
    def __init__(self, config: SourceConfig):
        """Initialize source with configuration.
        
        Args:
            config: Source configuration
        """
        self.config = config
        self.name = config.name
        self.weight = config.weight
        self.max_fetch = config.max_fetch
        
    @abstractmethod
    async def fetch(self) -> list[Article]:
        """Fetch articles from the source.
        
        Returns:
            List of Article objects
        """
        pass
    
    def normalize_score(self, article: Article) -> float:
        """Normalize article score based on source weight and other factors.
        
        Default implementation multiplies raw score by source weight.
        Override in subclasses for source-specific normalization.
        
        Args:
            article: Article to normalize score for
            
        Returns:
            Normalized score
        """
        base_score = article.raw_score or 0
        
        # Apply source weight
        weighted_score = base_score * self.weight
        
        # Apply recency bonus (articles from last 6 hours get boost)
        if article.published:
            hours_old = (datetime.utcnow() - article.published).total_seconds() / 3600
            recency_multiplier = max(0.5, 1.0 - (hours_old / 48))
            weighted_score *= recency_multiplier
        
        return weighted_score
    
    def _create_http_client(self, timeout: float = 30.0) -> httpx.AsyncClient:
        """Create an async HTTP client with default settings.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Configured httpx.AsyncClient
        """
        return httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; KindleNewsBot/1.0)"
            },
            follow_redirects=True,
        )
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, enabled={self.config.enabled})"
