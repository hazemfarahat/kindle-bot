"""Newsletter source implementation using IMAP."""

import email
import imaplib
import re
from datetime import datetime, timedelta
from email.header import decode_header
from typing import Optional

from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date

from ..config import get_config
from ..models import Article, SourceConfig, SourceType
from .base import BaseSource


class NewsletterSource(BaseSource):
    """Fetches articles from newsletters via IMAP."""
    
    def __init__(self, config: SourceConfig):
        """Initialize newsletter source."""
        super().__init__(config)
        self.sender_email = config.sender_email
        
        if not self.sender_email:
            raise ValueError(f"Newsletter source {config.name} requires sender_email")
    
    async def fetch(self) -> list[Article]:
        """Fetch articles from the latest newsletter.
        
        Returns:
            List of Article objects
        """
        app_config = get_config()
        
        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(
            app_config.imap_host,
            app_config.imap_port
        )
        
        try:
            # Login
            mail.login(app_config.smtp_user, app_config.smtp_password)
            mail.select("INBOX")
            
            # Search for emails from sender
            _, message_ids = mail.search(None, f'FROM "{self.sender_email}"')
            
            if not message_ids[0]:
                raise ValueError(f"No newsletters found from {self.sender_email}")
            
            # Get the most recent emails
            ids = message_ids[0].split()
            
            # Find a valid newsletter within the max age
            max_age = timedelta(hours=app_config.newsletter_max_age_hours)
            cutoff_date = datetime.utcnow() - max_age
            
            newsletter_content = None
            newsletter_date = None
            
            # Check emails from newest to oldest
            for msg_id in reversed(ids[-5:]):  # Check last 5 emails
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                
                if not msg_data or not msg_data[0]:
                    continue
                
                raw_email = msg_data[0][1]
                if isinstance(raw_email, bytes):
                    msg = email.message_from_bytes(raw_email)
                else:
                    msg = email.message_from_string(raw_email)
                
                # Get email date
                date_str = msg.get("Date", "")
                try:
                    email_date = parse_date(date_str)
                    if email_date.tzinfo:
                        email_date = email_date.replace(tzinfo=None)
                except (ValueError, TypeError):
                    email_date = datetime.utcnow()
                
                # Check if within age limit
                if email_date < cutoff_date:
                    if not app_config.newsletter_fallback_to_previous:
                        continue
                
                # Extract HTML content
                html_content = self._get_html_content(msg)
                if html_content:
                    newsletter_content = html_content
                    newsletter_date = email_date
                    break
            
            if not newsletter_content:
                raise ValueError(f"No recent newsletter found from {self.sender_email}")
            
            # Parse articles from newsletter
            articles = self._parse_newsletter(newsletter_content, newsletter_date)
            return articles[:self.max_fetch]
            
        finally:
            try:
                mail.logout()
            except Exception:
                pass
    
    def _get_html_content(self, msg: email.message.Message) -> Optional[str]:
        """Extract HTML content from email message.
        
        Args:
            msg: Email message
            
        Returns:
            HTML content or None
        """
        html_content = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_content = payload.decode(charset, errors="replace")
                        break
        else:
            content_type = msg.get_content_type()
            if content_type == "text/html":
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    html_content = payload.decode(charset, errors="replace")
        
        return html_content
    
    def _parse_newsletter(self, html: str, newsletter_date: datetime) -> list[Article]:
        """Parse articles from newsletter HTML.
        
        This method handles common newsletter formats from TLDR, Techmeme, etc.
        
        Args:
            html: Newsletter HTML content
            newsletter_date: Date of the newsletter
            
        Returns:
            List of Article objects
        """
        soup = BeautifulSoup(html, "lxml")
        articles = []
        seen_urls = set()
        
        # Find all links in the newsletter
        links = soup.find_all("a", href=True)
        
        position = 0
        for link in links:
            url = link.get("href", "").strip()
            
            # Skip non-article links
            if not self._is_article_url(url):
                continue
            
            # Skip duplicates
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Get link text as title
            title = link.get_text(strip=True)
            if not title or len(title) < 10:
                # Try to find title in parent elements
                title = self._find_title_near_link(link)
            
            if not title or len(title) < 10:
                continue
            
            # Skip generic newsletter link text
            skip_titles = [
                "view online", "view in browser", "read online",
                "sign up", "subscribe", "unsubscribe", "advertise",
                "forward", "share", "privacy policy", "terms",
                "got this from a friend", "click here",
                "track your referrals", "refer.tldr.tech",
                "apply here", "create your own role", "job posting",
                "together with", "sponsor", "save your spot",
                "see the full agenda", "join us", "register now",
                "take the quiz", "best bootstrapped", "sonar summit",
                "boardroom-ready", "virtual conference",
                "manage your subscriptions", "other newsletters",
            ]
            title_lower = title.lower()
            if any(skip in title_lower for skip in skip_titles):
                continue
            
            # Skip if title looks like a URL
            if title.startswith("http://") or title.startswith("https://"):
                continue
            
            # Skip Twitter/X handles (common in newsletters)
            if title.startswith("@") and title.endswith(":"):
                continue
            
            # Skip very short titles that are likely just names or labels
            # (unless they contain "minute read" which indicates TLDR articles)
            if len(title) < 25 and "minute read" not in title_lower:
                continue
            
            # For TLDR-style newsletters, prefer links with "(X minute read)" pattern
            # as these are the actual article links
            is_tldr_article = "minute read" in title_lower
            
            # Get summary from surrounding text
            summary = self._find_summary_near_link(link)
            
            # Position-based scoring (earlier in newsletter = more important)
            raw_score = max(0, 100 - (position * 3))
            
            articles.append(Article(
                title=title[:200],  # Truncate long titles
                url=url,
                source=self.name,
                source_type=SourceType.NEWSLETTER,
                raw_score=float(raw_score),
                position=position,
                published=newsletter_date,
                summary=summary[:500] if summary else "",
            ))
            
            position += 1
        
        return articles
    
    def _is_article_url(self, url: str) -> bool:
        """Check if URL looks like an article link.
        
        Args:
            url: URL to check
            
        Returns:
            True if likely an article URL
        """
        if not url:
            return False
        
        # Must be http(s)
        if not url.startswith(("http://", "https://")):
            return False
        
        # Skip common non-article URLs
        skip_patterns = [
            "unsubscribe",
            "mailto:",
            "javascript:",
            "twitter.com",
            "facebook.com",
            "linkedin.com/share",
            "reddit.com/submit",
            ".png",
            ".jpg",
            ".gif",
            ".svg",
            # Note: Don't block list-manage.com/track/click - those are article links
            "list-manage.com/subscribe",
            "list-manage.com/profile",
            "mailchimp.com",
            "email.mg.",
            "click.convertkit",
            "/sponsor",
            "/advertise",
            # Newsletter platform links (not articles)
            "campaign-archive.com",
            "forward-to-friend.com",
            "tldrnewsletter.com/web-version",
            "a.tldrnewsletter.com/web",
            "view-in-browser",
            "web-version",
            "preferences",
            "manage-preferences",
            # Referral/tracking links
            "refer.tldr.tech",
            "sparklp.co",
            "hub.sparklp",
        ]
        
        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        return True
    
    def _find_title_near_link(self, link) -> str:
        """Find article title near a link element.
        
        Args:
            link: BeautifulSoup link element
            
        Returns:
            Title text
        """
        # Check parent elements for heading-like content
        for parent in link.parents:
            if parent.name in ["td", "div", "li", "p"]:
                # Look for bold/strong text
                bold = parent.find(["strong", "b", "h1", "h2", "h3", "h4"])
                if bold:
                    text = bold.get_text(strip=True)
                    if len(text) > 10:
                        return text
                break
        
        return ""
    
    def _find_summary_near_link(self, link) -> str:
        """Find article summary near a link element.
        
        Args:
            link: BeautifulSoup link element
            
        Returns:
            Summary text
        """
        link_text = link.get_text(strip=True)
        
        # Look in parent container for text after the link
        for parent in link.parents:
            if parent.name in ["td", "div", "li", "tr"]:
                # Get full text content of the container
                full_text = parent.get_text(separator=" ", strip=True)
                
                # Remove the link text (title) from the beginning
                if full_text.startswith(link_text):
                    summary = full_text[len(link_text):].strip()
                elif link_text in full_text:
                    # Title might be in the middle - get text after it
                    idx = full_text.find(link_text)
                    summary = full_text[idx + len(link_text):].strip()
                else:
                    summary = full_text
                
                # Clean up common prefixes/suffixes
                summary = summary.lstrip("|-–—:•")
                summary = summary.strip()
                
                # Skip if it's just metadata like "(2 min read)" or Twitter handles
                if summary and len(summary) > 20:
                    # Don't return if it's mostly just another link or handle
                    if not summary.startswith("@") and not summary.startswith("http"):
                        return summary[:500]
                
                # If first parent didn't have good content, try next parent
                continue
        
        return ""
    
    def normalize_score(self, article: Article) -> float:
        """Normalize newsletter score.
        
        Newsletter articles are curated, so position is key.
        Earlier articles are typically more important.
        
        Args:
            article: Article to normalize
            
        Returns:
            Normalized score
        """
        return super().normalize_score(article)
