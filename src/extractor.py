"""Article content extraction with image handling."""

import asyncio
import base64
import hashlib
import io
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura
from PIL import Image

from .config import get_config
from .models import Article


# Paywall indicators
PAYWALL_INDICATORS = [
    "subscribe to read",
    "subscription required",
    "sign in to read",
    "premium content",
    "members only",
    "exclusive content",
    "register to continue",
    "create an account",
    "log in to access",
    "paywall",
    "paid subscribers",
]


class ContentExtractor:
    """Extracts full article content and images."""
    
    def __init__(self):
        """Initialize extractor with config."""
        self.config = get_config()
        self.max_images = self.config.max_images_per_article
        self.max_image_width = self.config.max_image_width
        self.image_quality = self.config.image_quality
        self.min_content_length = self.config.min_content_length
        self.timeout = self.config.extraction_timeout
        self.user_agent = self.config.user_agent
    
    async def extract_articles(self, articles: list[Article]) -> list[Article]:
        """Extract full content for multiple articles.
        
        Args:
            articles: List of articles to extract content for
            
        Returns:
            Articles with full_content populated
        """
        tasks = [self.extract_article(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        extracted = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Keep article with summary only
                article = articles[i]
                article.is_summary_only = True
                extracted.append(article)
            else:
                extracted.append(result)
        
        return extracted
    
    async def extract_article(self, article: Article) -> Article:
        """Extract full content for a single article.
        
        Args:
            article: Article to extract content for
            
        Returns:
            Article with full_content populated
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            ) as client:
                # Fetch the page
                response = await client.get(article.url)
                response.raise_for_status()
                html = response.text
                
                # Extract main content using trafilatura
                content = trafilatura.extract(
                    html,
                    include_images=True,
                    include_links=True,
                    include_formatting=True,
                    output_format="html",
                    url=article.url,
                )
                
                if not content:
                    # Fallback: try with fewer options
                    content = trafilatura.extract(
                        html,
                        output_format="html",
                    )
                
                # Check for paywall
                if self._is_paywalled(content, html):
                    article.is_summary_only = True
                    article.full_content = self._create_summary_content(article)
                    return article
                
                # Check content length
                if content and len(self._strip_html(content)) < self.min_content_length:
                    article.is_summary_only = True
                    article.full_content = self._create_summary_content(article)
                    return article
                
                if content:
                    # Process images
                    if self.config.include_images:
                        content, images = await self._process_images(
                            content, article.url, client
                        )
                        article.images = images
                    
                    article.full_content = content
                    article.is_summary_only = False
                else:
                    article.is_summary_only = True
                    article.full_content = self._create_summary_content(article)
                
                return article
                
        except Exception as e:
            # Extraction failed, use summary
            article.is_summary_only = True
            article.full_content = self._create_summary_content(article)
            return article
    
    def _is_paywalled(self, content: Optional[str], html: str) -> bool:
        """Check if content appears to be behind a paywall.
        
        Args:
            content: Extracted content
            html: Original HTML
            
        Returns:
            True if likely paywalled
        """
        text_to_check = (content or "") + html[:5000]
        text_lower = text_to_check.lower()
        
        for indicator in PAYWALL_INDICATORS:
            if indicator in text_lower:
                return True
        
        return False
    
    def _create_summary_content(self, article: Article) -> str:
        """Create HTML content from article summary.
        
        Args:
            article: Article with summary
            
        Returns:
            HTML content
        """
        summary = article.summary or "No summary available."
        return f"""
        <div class="summary-only">
            <p><em>Full article not available. Summary:</em></p>
            <p>{summary}</p>
        </div>
        """
    
    async def _process_images(
        self,
        content: str,
        base_url: str,
        client: httpx.AsyncClient
    ) -> tuple[str, list[str]]:
        """Download and embed images in content.
        
        Args:
            content: HTML content with image tags
            base_url: Base URL for resolving relative URLs
            client: HTTP client
            
        Returns:
            Tuple of (content with embedded images, list of image data URIs)
        """
        # Find all image tags
        img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
        matches = list(img_pattern.finditer(content))
        
        if not matches:
            return content, []
        
        # Limit number of images
        matches = matches[:self.max_images]
        
        images = []
        replacements = []
        
        for match in matches:
            img_tag = match.group(0)
            img_url = match.group(1)
            
            # Resolve relative URLs
            if not img_url.startswith(("http://", "https://", "data:")):
                img_url = urljoin(base_url, img_url)
            
            # Skip data URIs (already embedded)
            if img_url.startswith("data:"):
                continue
            
            try:
                # Download image
                img_data = await self._download_image(img_url, client)
                if img_data:
                    # Create data URI
                    data_uri = f"data:image/jpeg;base64,{img_data}"
                    images.append(data_uri)
                    
                    # Create new img tag with data URI
                    new_tag = f'<img src="{data_uri}" alt="Article image" style="max-width:100%"/>'
                    replacements.append((img_tag, new_tag))
            except Exception:
                # Skip failed images
                continue
        
        # Apply replacements
        for old, new in replacements:
            content = content.replace(old, new, 1)
        
        return content, images
    
    async def _download_image(
        self,
        url: str,
        client: httpx.AsyncClient
    ) -> Optional[str]:
        """Download and process an image.
        
        Args:
            url: Image URL
            client: HTTP client
            
        Returns:
            Base64-encoded JPEG data or None
        """
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            
            # Load image
            img = Image.open(io.BytesIO(response.content))
            
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")
            
            # Resize if too wide
            if img.width > self.max_image_width:
                ratio = self.max_image_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize(
                    (self.max_image_width, new_height),
                    Image.Resampling.LANCZOS
                )
            
            # Save as JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=self.image_quality, optimize=True)
            
            return base64.b64encode(buffer.getvalue()).decode("ascii")
            
        except Exception:
            return None
    
    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from text.
        
        Args:
            html: HTML content
            
        Returns:
            Plain text
        """
        clean = re.sub(r'<[^>]+>', '', html)
        clean = ' '.join(clean.split())
        return clean


async def extract_content(articles: list[Article]) -> list[Article]:
    """Convenience function to extract content for articles.
    
    Args:
        articles: Articles to extract
        
    Returns:
        Articles with content extracted
    """
    extractor = ContentExtractor()
    return await extractor.extract_articles(articles)
