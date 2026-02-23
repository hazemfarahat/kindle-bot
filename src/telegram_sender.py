"""Telegram bot sender for delivering EPUB files."""

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class TelegramSender:
    """Send EPUB files via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram sender.

        Args:
            bot_token: Bot token from @BotFather
            chat_id: Target chat ID to send files to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"

    async def send_epub(self, file_path: Path) -> None:
        """Send EPUB file to Telegram chat.

        Args:
            file_path: Path to the EPUB file to send

        Raises:
            Exception: If Telegram API returns an error
            FileNotFoundError: If the EPUB file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {file_path}")

        url = f"{self.api_base}/sendDocument"
        logger.info(f"Sending {file_path.name} to Telegram chat {self.chat_id}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(file_path, "rb") as f:
                files = {"document": (file_path.name, f, "application/epub+zip")}
                data = {"chat_id": self.chat_id}
                response = await client.post(url, data=data, files=files)

        result = response.json()
        if not result.get("ok"):
            error_desc = result.get("description", "Unknown error")
            logger.error(f"Telegram API error: {error_desc}")
            raise Exception(f"Telegram API error: {error_desc}")

        logger.info(f"Successfully sent {file_path.name} to Telegram")

    async def send_message(self, text: str, parse_mode: str = "Markdown") -> None:
        """Send a text message to Telegram chat.

        Args:
            text: Message text (supports Markdown/HTML)
            parse_mode: Message format - "Markdown" or "HTML"

        Raises:
            Exception: If Telegram API returns an error
        """
        url = f"{self.api_base}/sendMessage"
        logger.info(f"Sending message to Telegram chat {self.chat_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,  # Avoid link previews cluttering message
            }
            response = await client.post(url, data=data)

        result = response.json()
        if not result.get("ok"):
            error_desc = result.get("description", "Unknown error")
            logger.error(f"Telegram API error: {error_desc}")
            raise Exception(f"Telegram API error: {error_desc}")

        logger.info("Successfully sent message to Telegram")
