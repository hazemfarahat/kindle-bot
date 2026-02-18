"""Data models for Kindle News Digest."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class SourceType(Enum):
    """Type of news source."""
    API = "api"
    RSS = "rss"
    JSON = "json"
    NEWSLETTER = "newsletter"


@dataclass
class Article:
    """Represents a news article."""
    title: str
    url: str
    source: str
    source_type: SourceType
    
    # Scoring
    raw_score: float = 0.0
    normalized_score: float = 0.0
    position: int = 0  # For curated sources (position in list)
    
    # Content
    summary: str = ""
    full_content: Optional[str] = None
    is_summary_only: bool = False
    images: list[str] = field(default_factory=list)
    
    # Metadata
    author: Optional[str] = None
    published: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    
    # For deduplication
    canonical_url: str = ""
    title_hash: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "source_type": self.source_type.value,
            "raw_score": self.raw_score,
            "normalized_score": self.normalized_score,
            "position": self.position,
            "summary": self.summary,
            "full_content": self.full_content,
            "is_summary_only": self.is_summary_only,
            "images": self.images,
            "author": self.author,
            "published": self.published.isoformat() if self.published else None,
            "fetched_at": self.fetched_at.isoformat(),
            "canonical_url": self.canonical_url,
            "title_hash": self.title_hash,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create Article from dictionary."""
        return cls(
            title=data["title"],
            url=data["url"],
            source=data["source"],
            source_type=SourceType(data["source_type"]),
            raw_score=data.get("raw_score", 0.0),
            normalized_score=data.get("normalized_score", 0.0),
            position=data.get("position", 0),
            summary=data.get("summary", ""),
            full_content=data.get("full_content"),
            is_summary_only=data.get("is_summary_only", False),
            images=data.get("images", []),
            author=data.get("author"),
            published=datetime.fromisoformat(data["published"]) if data.get("published") else None,
            fetched_at=datetime.fromisoformat(data["fetched_at"]) if data.get("fetched_at") else datetime.utcnow(),
            canonical_url=data.get("canonical_url", ""),
            title_hash=data.get("title_hash", ""),
        )


@dataclass
class SourceError:
    """Represents an error from a source."""
    source: str
    error: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DigestResult:
    """Result of generating a digest."""
    articles: list[Article]
    errors: list[SourceError]
    digest_type: str  # "daily", "weekly", or "run-once"
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "articles": [a.to_dict() for a in self.articles],
            "errors": [e.to_dict() for e in self.errors],
            "digest_type": self.digest_type,
            "generated_at": self.generated_at.isoformat(),
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class SourceConfig:
    """Configuration for a news source."""
    name: str
    enabled: bool
    source_type: SourceType
    url: str = ""
    weight: float = 1.0
    max_fetch: int = 20
    sender_email: str = ""  # For newsletter sources
    
    @classmethod
    def from_dict(cls, name: str, data: dict) -> "SourceConfig":
        """Create SourceConfig from dictionary."""
        return cls(
            name=name,
            enabled=data.get("enabled", True),
            source_type=SourceType(data.get("type", "rss")),
            url=data.get("url", ""),
            weight=data.get("weight", 1.0),
            max_fetch=data.get("max_fetch", 20),
            sender_email=data.get("sender_email", ""),
        )
