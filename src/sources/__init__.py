"""News source implementations."""

from .base import BaseSource
from .hackernews import HackerNewsSource
from .lobsters import LobstersSource
from .devto import DevToSource
from .rss import RSSSource
from .newsletter import NewsletterSource

from ..models import SourceConfig, SourceType

# Source registry - maps source type to implementation
SOURCE_REGISTRY: dict[str, type[BaseSource]] = {
    "hackernews": HackerNewsSource,
    "lobsters": LobstersSource,
    "devto": DevToSource,
    "mit_tech_review": RSSSource,
    "techcrunch": RSSSource,
    "tldr": NewsletterSource,
    "techmeme": NewsletterSource,
}


def create_source(config: SourceConfig) -> BaseSource:
    """Create a source instance from configuration.
    
    Args:
        config: Source configuration
        
    Returns:
        BaseSource instance
        
    Raises:
        ValueError: If source type is not supported
    """
    # Try to get specific source implementation first
    if config.name in SOURCE_REGISTRY:
        return SOURCE_REGISTRY[config.name](config)
    
    # Fall back to type-based lookup
    type_registry = {
        SourceType.RSS: RSSSource,
        SourceType.JSON: LobstersSource,  # JSON feeds similar to Lobsters
        SourceType.NEWSLETTER: NewsletterSource,
    }
    
    source_class = type_registry.get(config.source_type)
    if source_class is None:
        raise ValueError(f"Unsupported source type: {config.source_type}")
    
    return source_class(config)


__all__ = [
    "BaseSource",
    "HackerNewsSource",
    "LobstersSource",
    "DevToSource",
    "RSSSource",
    "NewsletterSource",
    "SOURCE_REGISTRY",
    "create_source",
]
