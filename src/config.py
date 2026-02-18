"""Configuration loader for Kindle News Digest."""

import os
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from dotenv import load_dotenv

from .models import SourceConfig, SourceType


class Config:
    """Application configuration."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration from YAML file and environment variables."""
        # Load environment variables
        load_dotenv()
        
        # Load YAML config
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(str(config_path), "r") as f:
            self._config = yaml.safe_load(f)
        
        # Parse source configurations
        self._sources: dict[str, SourceConfig] = {}
        for name, data in self._config.get("sources", {}).items():
            self._sources[name] = SourceConfig.from_dict(name, data)
    
    # -------------------------------------------------------------------------
    # Environment variables (secrets)
    # -------------------------------------------------------------------------
    
    @property
    def smtp_user(self) -> str:
        """Gmail username for SMTP."""
        return os.getenv("SMTP_USER", "")
    
    @property
    def smtp_password(self) -> str:
        """Gmail app password for SMTP."""
        return os.getenv("SMTP_PASSWORD", "")
    
    @property
    def sender_email(self) -> str:
        """Email address to send from."""
        return os.getenv("SENDER_EMAIL", self.smtp_user)
    
    @property
    def kindle_email(self) -> str:
        """Kindle device email address."""
        return os.getenv("KINDLE_EMAIL", "")
    
    # -------------------------------------------------------------------------
    # Digest settings
    # -------------------------------------------------------------------------
    
    @property
    def daily_enabled(self) -> bool:
        """Whether daily digest is enabled."""
        return self._config.get("digest", {}).get("daily", {}).get("enabled", True)
    
    @property
    def daily_article_count(self) -> int:
        """Number of articles in daily digest."""
        return self._config.get("digest", {}).get("daily", {}).get("article_count", 10)
    
    @property
    def weekly_enabled(self) -> bool:
        """Whether weekly digest is enabled."""
        return self._config.get("digest", {}).get("weekly", {}).get("enabled", True)
    
    @property
    def weekly_article_count(self) -> int:
        """Number of articles in weekly digest."""
        return self._config.get("digest", {}).get("weekly", {}).get("article_count", 25)
    
    @property
    def weekly_day(self) -> str:
        """Day of week for weekly digest."""
        return self._config.get("digest", {}).get("weekly", {}).get("day", "saturday")
    
    # -------------------------------------------------------------------------
    # Sources
    # -------------------------------------------------------------------------
    
    @property
    def sources(self) -> dict[str, SourceConfig]:
        """All source configurations."""
        return self._sources
    
    def get_enabled_sources(self) -> list[SourceConfig]:
        """Get list of enabled sources."""
        return [s for s in self._sources.values() if s.enabled]
    
    def get_source(self, name: str) -> Optional[SourceConfig]:
        """Get source configuration by name."""
        return self._sources.get(name)
    
    # -------------------------------------------------------------------------
    # Extraction settings
    # -------------------------------------------------------------------------
    
    @property
    def include_images(self) -> bool:
        """Whether to include images in articles."""
        return self._config.get("extraction", {}).get("include_images", True)
    
    @property
    def max_images_per_article(self) -> int:
        """Maximum number of images per article."""
        return self._config.get("extraction", {}).get("max_images_per_article", 5)
    
    @property
    def max_image_width(self) -> int:
        """Maximum image width in pixels."""
        return self._config.get("extraction", {}).get("max_image_width", 600)
    
    @property
    def image_quality(self) -> int:
        """JPEG image quality (1-100)."""
        return self._config.get("extraction", {}).get("image_quality", 85)
    
    @property
    def paywall_fallback(self) -> str:
        """What to do when article is paywalled: 'summary' or 'skip'."""
        return self._config.get("extraction", {}).get("paywall_fallback", "summary")
    
    @property
    def min_content_length(self) -> int:
        """Minimum content length to consider article fully extracted."""
        return self._config.get("extraction", {}).get("min_content_length", 500)
    
    @property
    def extraction_timeout(self) -> int:
        """Timeout for article extraction in seconds."""
        return self._config.get("extraction", {}).get("timeout_seconds", 30)
    
    @property
    def user_agent(self) -> str:
        """User agent string for HTTP requests."""
        return self._config.get("extraction", {}).get(
            "user_agent",
            "Mozilla/5.0 (compatible; KindleNewsBot/1.0)"
        )
    
    # -------------------------------------------------------------------------
    # Newsletter settings
    # -------------------------------------------------------------------------
    
    @property
    def newsletter_fallback_to_previous(self) -> bool:
        """Whether to use yesterday's newsletter if today's not available."""
        return self._config.get("newsletter", {}).get("fallback_to_previous", True)
    
    @property
    def newsletter_max_age_hours(self) -> int:
        """Maximum age of newsletter to use in hours."""
        return self._config.get("newsletter", {}).get("max_age_hours", 36)
    
    @property
    def imap_host(self) -> str:
        """IMAP server host."""
        return self._config.get("newsletter", {}).get("imap_host", "imap.gmail.com")
    
    @property
    def imap_port(self) -> int:
        """IMAP server port."""
        return self._config.get("newsletter", {}).get("imap_port", 993)
    
    # -------------------------------------------------------------------------
    # EPUB settings
    # -------------------------------------------------------------------------
    
    @property
    def epub_title_format(self) -> str:
        """Format string for EPUB title."""
        return self._config.get("epub", {}).get("title_format", "Tech Digest - {date}")
    
    @property
    def epub_weekly_title_format(self) -> str:
        """Format string for weekly EPUB title."""
        return self._config.get("epub", {}).get(
            "weekly_title_format",
            "Weekly Tech Digest - {week_start} to {week_end}"
        )
    
    @property
    def epub_author(self) -> str:
        """EPUB author name."""
        return self._config.get("epub", {}).get("author", "Kindle News Bot")
    
    @property
    def epub_language(self) -> str:
        """EPUB language code."""
        return self._config.get("epub", {}).get("language", "en")
    
    @property
    def epub_include_toc(self) -> bool:
        """Whether to include table of contents."""
        return self._config.get("epub", {}).get("include_toc", True)
    
    @property
    def epub_include_source_badge(self) -> bool:
        """Whether to include source badge on articles."""
        return self._config.get("epub", {}).get("include_source_badge", True)
    
    @property
    def epub_include_original_link(self) -> bool:
        """Whether to include original article link."""
        return self._config.get("epub", {}).get("include_original_link", True)
    
    @property
    def epub_include_score(self) -> bool:
        """Whether to include article score."""
        return self._config.get("epub", {}).get("include_score", True)
    
    @property
    def epub_font_family(self) -> str:
        """Font family for EPUB."""
        return self._config.get("epub", {}).get("font_family", "Georgia, serif")
    
    @property
    def epub_max_title_length(self) -> int:
        """Maximum title length in TOC."""
        return self._config.get("epub", {}).get("max_title_length", 100)
    
    # -------------------------------------------------------------------------
    # Email settings
    # -------------------------------------------------------------------------
    
    @property
    def smtp_host(self) -> str:
        """SMTP server host."""
        return self._config.get("email", {}).get("smtp_host", "smtp.gmail.com")
    
    @property
    def smtp_port(self) -> int:
        """SMTP server port."""
        return self._config.get("email", {}).get("smtp_port", 587)
    
    @property
    def smtp_use_tls(self) -> bool:
        """Whether to use TLS for SMTP."""
        return self._config.get("email", {}).get("use_tls", True)
    
    @property
    def email_daily_subject(self) -> str:
        """Subject line format for daily digest."""
        return self._config.get("email", {}).get("daily_subject", "Daily Tech Digest - {date}")
    
    @property
    def email_weekly_subject(self) -> str:
        """Subject line format for weekly digest."""
        return self._config.get("email", {}).get(
            "weekly_subject",
            "Weekly Tech Digest - Week of {week_start}"
        )

    # -------------------------------------------------------------------------
    # Delivery settings
    # -------------------------------------------------------------------------

    @property
    def delivery_method(self) -> str:
        """Default delivery method: none, email, telegram, or both."""
        return self._config.get("delivery", {}).get("method", "email")

    # -------------------------------------------------------------------------
    # Telegram settings
    # -------------------------------------------------------------------------

    @property
    def telegram_bot_token(self) -> str:
        """Telegram bot token from @BotFather."""
        return os.getenv("TELEGRAM_BOT_TOKEN", "")

    @property
    def telegram_chat_id(self) -> str:
        """Telegram chat ID to send files to."""
        return os.getenv("TELEGRAM_CHAT_ID", "")


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file."""
    global _config
    _config = Config(config_path)
    return _config
