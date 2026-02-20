# AGENTS.md - Kindle News Digest

This document provides guidance for AI coding agents working in this repository.

## Project Overview

**Kindle News Digest** is a Python automation tool that:
- Collects tech news from multiple sources (Hacker News, Lobsters, Dev.to, TechCrunch, etc.)
- Aggregates, deduplicates, and ranks articles
- Extracts full article content with images
- Generates EPUB books and delivers them to Kindle via email or Telegram

**Tech Stack:** Python 3.12+, asyncio, httpx, ebooklib, trafilatura

## Project Structure

```
src/
├── main.py              # CLI entry point (argparse)
├── config.py            # Configuration loader (YAML + env vars)
├── models.py            # Data models (dataclasses)
├── aggregator.py        # Article aggregation & ranking
├── extractor.py         # Content extraction with images
├── epub_builder.py      # EPUB generation
├── emailer.py           # Email sender for Kindle
├── telegram_sender.py   # Telegram bot sender
├── cache.py             # Weekly article cache management
└── sources/             # News source implementations
    ├── __init__.py      # Source registry and factory
    ├── base.py          # Abstract base class
    ├── hackernews.py    # Hacker News API
    ├── lobsters.py      # Lobsters JSON feed
    ├── devto.py         # Dev.to API
    ├── rss.py           # Generic RSS feeds
    └── newsletter.py    # IMAP newsletter parsing
```

## Build/Run Commands

### Installation
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Generate EPUB only (no delivery)
python -m src.main --run-once --delivery none

# Run with email delivery (default)
python -m src.main --run-once

# Run with Telegram delivery
python -m src.main --run-once --delivery telegram

# Custom article count
python -m src.main --run-once --articles 15

# Custom output path
python -m src.main --run-once --output ~/Desktop/digest.epub

# Daily/weekly scheduled modes
python -m src.main --type daily
python -m src.main --type weekly --cache-dir cache/
```

### Testing
**No test suite exists.** When adding tests, use pytest:
```bash
pip install pytest pytest-asyncio
pytest tests/                    # Run all tests
pytest tests/test_models.py      # Run single test file
pytest tests/test_models.py::test_article_to_dict -v  # Run single test
```

### Linting/Formatting (Not Configured)
Recommended tools if adding:
```bash
pip install ruff mypy
ruff check src/                  # Lint
ruff format src/                 # Format
mypy src/                        # Type check
```

## Code Style Guidelines

### Import Order
1. Standard library imports
2. Third-party imports (no blank line between groups)
3. Local imports (relative within package)

```python
import asyncio
import hashlib
from datetime import datetime
from typing import Optional

import httpx
from thefuzz import fuzz

from .config import get_config
from .models import Article, SourceError
from ..models import Article  # Parent package relative
```

### Naming Conventions
- **Classes:** PascalCase (`ArticleCache`, `ContentExtractor`)
- **Functions/methods:** snake_case (`extract_content`, `normalize_score`)
- **Private methods:** Single underscore prefix (`_fetch_story`, `_create_http_client`)
- **Constants:** UPPER_SNAKE_CASE (`TRACKING_PARAMS`, `PAYWALL_INDICATORS`)
- **Variables:** snake_case (`all_articles`, `epub_path`)

### Type Hints
Use type hints extensively throughout the codebase:
```python
def send_to_kindle(
    self,
    epub_path: str,
    subject: Optional[str] = None,
    digest_type: str = "daily"
) -> bool:

async def aggregate(self, top_n: int = 10) -> tuple[list[Article], list[SourceError]]:
```

- Use `Optional[T]` for nullable types
- Use Python 3.9+ style: `list[T]`, `dict[K, V]` (not `List`, `Dict`)
- Always include return type annotations

### Data Models
Use `@dataclass` with serialization methods:
```python
@dataclass
class Article:
    title: str
    url: str
    images: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        ...
    
    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create from dictionary."""
        ...
```

### Async Patterns
- Use `async def` for I/O-bound operations
- Use `asyncio.gather(*tasks, return_exceptions=True)` for parallel execution
- Use `async with` for HTTP clients
- Provide sync convenience functions:
```python
async def extract_content(articles: list[Article]) -> list[Article]:
    extractor = ContentExtractor()
    return await extractor.extract_articles(articles)
```

### Class Structure
- `__init__` accepts configuration
- Public methods for main operations
- Private methods (underscore-prefixed) for internal logic
- Module-level convenience functions that instantiate and use classes

### Error Handling
- Use try/except with specific exception types
- Return empty results or fallback values on errors (fail gracefully)
- Use `SourceError` dataclass to collect errors without stopping
- Raise `ValueError` for configuration errors:
```python
if not self.config.smtp_user:
    raise ValueError("SMTP_USER not configured")
```

### Docstrings
Use Google-style docstrings:
```python
def normalize_url(self, url: str) -> str:
    """Normalize URL for deduplication.
    
    Removes tracking parameters, normalizes scheme, etc.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
```

### Abstract Base Classes
Use ABC pattern for source interfaces:
```python
class BaseSource(ABC):
    @abstractmethod
    async def fetch(self) -> list[Article]:
        pass
```

## Configuration

- **config.yaml:** Main application configuration
- **.env:** Environment variables for secrets (SMTP_USER, KINDLE_EMAIL, etc.)
- Use `get_config()` singleton pattern to access configuration

## Key Dependencies

- `httpx` - Async HTTP client
- `feedparser` - RSS/Atom feed parsing
- `trafilatura` - Web article extraction
- `ebooklib` - EPUB generation
- `Pillow` - Image processing
- `beautifulsoup4` + `lxml` - HTML parsing
- `thefuzz` - Fuzzy string matching for deduplication
