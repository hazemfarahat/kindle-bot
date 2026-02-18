"""Article aggregation, deduplication, and ranking."""

import asyncio
import hashlib
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from thefuzz import fuzz

from .config import get_config
from .models import Article, SourceConfig, SourceError
from .sources import create_source, BaseSource


class Aggregator:
    """Aggregates articles from multiple sources."""
    
    # URL parameters to remove for deduplication
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "ref", "source", "via", "campaign", "cid", "mc_cid", "mc_eid",
        "fbclid", "gclid", "msclkid", "twclid", "li_fat_id",
    }
    
    def __init__(self, sources: Optional[list[SourceConfig]] = None):
        """Initialize aggregator.
        
        Args:
            sources: List of source configurations. If None, uses enabled sources from config.
        """
        config = get_config()
        if sources is None:
            sources = config.get_enabled_sources()
        
        self.source_configs = sources
        self.sources: list[BaseSource] = []
        
        for source_config in sources:
            try:
                source = create_source(source_config)
                self.sources.append(source)
            except Exception as e:
                print(f"Warning: Failed to create source {source_config.name}: {e}")
    
    async def fetch_all(self) -> tuple[list[Article], list[SourceError]]:
        """Fetch articles from all sources.
        
        Returns:
            Tuple of (articles, errors)
        """
        tasks = [self._fetch_source(source) for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        all_articles = []
        all_errors = []
        
        for articles, errors in results:
            all_articles.extend(articles)
            all_errors.extend(errors)
        
        return all_articles, all_errors
    
    async def _fetch_source(self, source: BaseSource) -> tuple[list[Article], list[SourceError]]:
        """Fetch articles from a single source.
        
        Args:
            source: Source to fetch from
            
        Returns:
            Tuple of (articles, errors)
        """
        try:
            articles = await source.fetch()
            
            # Normalize scores for each article
            for article in articles:
                article.normalized_score = source.normalize_score(article)
                article.canonical_url = self._normalize_url(article.url)
                article.title_hash = self._hash_title(article.title)
            
            return articles, []
            
        except Exception as e:
            error = SourceError(
                source=source.name,
                error=str(e),
                timestamp=datetime.utcnow(),
            )
            return [], [error]
    
    def deduplicate(self, articles: list[Article]) -> list[Article]:
        """Remove duplicate articles.
        
        Articles are considered duplicates if they have:
        1. The same canonical URL
        2. Very similar titles (fuzzy match)
        
        When duplicates are found, we keep the one with the higher score
        and boost its score (appearing in multiple sources = more relevant).
        
        Args:
            articles: List of articles to deduplicate
            
        Returns:
            Deduplicated list of articles
        """
        seen_urls: dict[str, Article] = {}
        seen_titles: dict[str, Article] = {}
        
        for article in articles:
            canonical_url = article.canonical_url or self._normalize_url(article.url)
            title_hash = article.title_hash or self._hash_title(article.title)
            
            # Check URL match
            if canonical_url in seen_urls:
                existing = seen_urls[canonical_url]
                # Keep higher score, boost for appearing multiple times
                if article.normalized_score > existing.normalized_score:
                    # Replace with higher scored article
                    article.normalized_score *= 1.2  # 20% boost
                    seen_urls[canonical_url] = article
                    seen_titles[title_hash] = article
                else:
                    existing.normalized_score *= 1.2  # 20% boost
                continue
            
            # Check fuzzy title match
            matched_title = None
            for existing_hash, existing in seen_titles.items():
                # Use fuzzy matching for title comparison
                similarity = fuzz.ratio(article.title.lower(), existing.title.lower())
                if similarity > 85:  # 85% similarity threshold
                    matched_title = existing_hash
                    break
            
            if matched_title:
                existing = seen_titles[matched_title]
                if article.normalized_score > existing.normalized_score:
                    article.normalized_score *= 1.1  # 10% boost
                    seen_titles[matched_title] = article
                    seen_urls[canonical_url] = article
                else:
                    existing.normalized_score *= 1.1  # 10% boost
                continue
            
            # New unique article
            seen_urls[canonical_url] = article
            seen_titles[title_hash] = article
        
        return list(seen_urls.values())
    
    def rank(self, articles: list[Article], top_n: int = 10) -> list[Article]:
        """Rank articles by normalized score.
        
        Args:
            articles: List of articles to rank
            top_n: Number of top articles to return
            
        Returns:
            Top N articles sorted by score (descending)
        """
        sorted_articles = sorted(
            articles,
            key=lambda a: a.normalized_score,
            reverse=True
        )
        return sorted_articles[:top_n]
    
    async def aggregate(self, top_n: int = 10) -> tuple[list[Article], list[SourceError]]:
        """Full aggregation pipeline: fetch, dedupe, rank.
        
        Args:
            top_n: Number of top articles to return
            
        Returns:
            Tuple of (top articles, errors)
        """
        # Fetch from all sources
        all_articles, errors = await self.fetch_all()
        
        if not all_articles:
            return [], errors
        
        # Deduplicate
        unique_articles = self.deduplicate(all_articles)
        
        # Rank and return top N
        top_articles = self.rank(unique_articles, top_n)
        
        return top_articles, errors
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication.
        
        Removes tracking parameters, normalizes scheme, etc.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        try:
            parsed = urlparse(url)
            
            # Remove www prefix
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            
            # Remove tracking parameters
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=False)
                filtered_params = {
                    k: v for k, v in params.items()
                    if k.lower() not in self.TRACKING_PARAMS
                }
                query = urlencode(filtered_params, doseq=True) if filtered_params else ""
            else:
                query = ""
            
            # Remove fragment
            fragment = ""
            
            # Normalize path (remove trailing slash)
            path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
            
            # Rebuild URL
            normalized = urlunparse((
                "https",  # Normalize to https
                netloc,
                path,
                parsed.params,
                query,
                fragment,
            ))
            
            return normalized
            
        except Exception:
            return url.lower()
    
    def _hash_title(self, title: str) -> str:
        """Create a hash of the title for comparison.
        
        Normalizes the title before hashing.
        
        Args:
            title: Article title
            
        Returns:
            MD5 hash of normalized title
        """
        # Normalize: lowercase, remove punctuation, collapse whitespace
        normalized = title.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = ' '.join(normalized.split())
        
        return hashlib.md5(normalized.encode()).hexdigest()


async def aggregate_articles(top_n: int = 10) -> tuple[list[Article], list[SourceError]]:
    """Convenience function to aggregate articles.
    
    Args:
        top_n: Number of top articles to return
        
    Returns:
        Tuple of (top articles, errors)
    """
    aggregator = Aggregator()
    return await aggregator.aggregate(top_n)
