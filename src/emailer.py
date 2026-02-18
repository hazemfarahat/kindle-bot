"""Email sender for delivering EPUB to Kindle."""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from .config import get_config


class Emailer:
    """Sends EPUB files to Kindle via email."""
    
    def __init__(self):
        """Initialize emailer with config."""
        self.config = get_config()
    
    def send_to_kindle(
        self,
        epub_path: str,
        subject: Optional[str] = None,
        digest_type: str = "daily"
    ) -> bool:
        """Send EPUB file to Kindle email address.
        
        Args:
            epub_path: Path to EPUB file
            subject: Email subject (optional)
            digest_type: Type of digest for default subject
            
        Returns:
            True if sent successfully
        """
        # Validate credentials
        if not self.config.smtp_user:
            raise ValueError("SMTP_USER not configured")
        if not self.config.smtp_password:
            raise ValueError("SMTP_PASSWORD not configured")
        if not self.config.kindle_email:
            raise ValueError("KINDLE_EMAIL not configured")
        
        # Generate subject if not provided
        if subject is None:
            from datetime import datetime
            now = datetime.now()
            if digest_type == "weekly":
                from datetime import timedelta
                week_start = now - timedelta(days=now.weekday())
                subject = self.config.email_weekly_subject.format(
                    week_start=week_start.strftime("%b %d")
                )
            else:
                subject = self.config.email_daily_subject.format(
                    date=now.strftime("%b %d, %Y")
                )
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = self.config.sender_email
        msg["To"] = self.config.kindle_email
        msg["Subject"] = subject
        
        # Add body (Kindle ignores this, but good for debugging)
        body = f"Your {digest_type} tech digest is attached."
        msg.attach(MIMEText(body, "plain"))
        
        # Attach EPUB
        epub_file = Path(epub_path)
        if not epub_file.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")
        
        with open(epub_file, "rb") as f:
            epub_data = f.read()
        
        attachment = MIMEApplication(epub_data, _subtype="epub+zip")
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=epub_file.name
        )
        msg.attach(attachment)
        
        # Send email
        try:
            if self.config.smtp_use_tls:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port)
            
            server.login(self.config.smtp_user, self.config.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            raise ValueError(f"SMTP authentication failed. Check your App Password. Error: {e}")
        except smtplib.SMTPException as e:
            raise RuntimeError(f"Failed to send email: {e}")
    
    def test_connection(self) -> bool:
        """Test SMTP connection without sending email.
        
        Returns:
            True if connection successful
        """
        try:
            if self.config.smtp_use_tls:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port)
            
            server.login(self.config.smtp_user, self.config.smtp_password)
            server.quit()
            
            return True
            
        except Exception:
            return False


def send_epub_to_kindle(
    epub_path: str,
    subject: Optional[str] = None,
    digest_type: str = "daily"
) -> bool:
    """Convenience function to send EPUB to Kindle.
    
    Args:
        epub_path: Path to EPUB file
        subject: Email subject
        digest_type: Type of digest
        
    Returns:
        True if sent successfully
    """
    emailer = Emailer()
    return emailer.send_to_kindle(epub_path, subject, digest_type)
