"""Hacker News source implementation."""

import asyncio
from datetime import datetime
from typing import Optional

import httpx

from ..models import Article, SourceConfig, SourceType
from .base import BaseSource


class HackerNewsSource(BaseSource):
    """Fetches top stories from Hacker News API."""
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self, config: SourceConfig):
        """Initialize Hacker News source."""
        super().__init__(config)
        self.base_url = config.url or self.BASE_URL
    
    async def fetch(self) -> list[Article]:
        """Fetch top stories from Hacker News.
        
        Returns:
            List of Article objects
        """
        async with self._create_http_client() as client:
            # Get top story IDs
            top_stories_url = f"{self.base_url}/topstories.json"
            response = await client.get(top_stories_url)
            response.raise_for_status()
            story_ids = response.json()[:self.max_fetch]
            
            # Fetch story details in parallel
            tasks = [
                self._fetch_story(client, story_id)
                for story_id in story_ids
            ]
            stories = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out failed fetches
            articles = []
            for i, story in enumerate(stories):
                if isinstance(story, Exception):
                    continue
                if story is not None:
                    story.position = i
                    articles.append(story)
            
            return articles
    
    async def _fetch_story(self, client: httpx.AsyncClient, story_id: int) -> Optional[Article]:
        """Fetch a single story by ID.
        
        Args:
            client: HTTP client
            story_id: Hacker News story ID
            
        Returns:
            Article object or None if story should be skipped
        """
        url = f"{self.base_url}/item/{story_id}.json"
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data is None:
            return None
        
        # Skip if no URL (Ask HN, Show HN text posts, etc.)
        story_url = data.get("url")
        if not story_url:
            # Could use HN discussion page as fallback
            story_url = f"https://news.ycombinator.com/item?id={story_id}"
        
        # Parse timestamp
        published = None
        if data.get("time"):
            published = datetime.utcfromtimestamp(data["time"])
        
        return Article(
            title=data.get("title", "Untitled"),
            url=story_url,
            source=self.name,
            source_type=SourceType.API,
            raw_score=float(data.get("score", 0)),
            author=data.get("by"),
            published=published,
            summary=f"Score: {data.get('score', 0)} | Comments: {data.get('descendants', 0)}",
        )
    
    def normalize_score(self, article: Article) -> float:
        """Normalize Hacker News score.
        
        HN scores typically range from 0-500+ for front page stories.
        We use the raw score directly with weight applied.
        
        Args:
            article: Article to normalize
            
        Returns:
            Normalized score
        """
        # HN scores are already well-scaled, just apply weight and recency
        return super().normalize_score(article)
