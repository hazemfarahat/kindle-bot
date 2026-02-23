"""AI-powered article summarization using OpenAI."""

import logging
from datetime import datetime

from openai import AsyncOpenAI

from .config import get_config
from .models import Article

logger = logging.getLogger(__name__)


class Summarizer:
    """Generate AI summaries of article collections."""

    SYSTEM_PROMPT = """You are a tech news curator creating daily briefings for busy tech professionals.
Your summaries are concise, insightful, and focus on why stories matter, not just what happened.
Write in a professional but conversational tone. Do not use emojis."""

    EPUB_PROMPT_TEMPLATE = """Summarize these {article_count} articles into a cohesive ~{max_words} word digest.

Articles:
{articles_text}

Format your response as:

**Top Stories**
[2-3 sentences about the most significant story and why it matters]

**Key Developments**
[Brief coverage of other notable stories, grouped by theme if applicable]

**Quick Hits**
- [One-liner for remaining articles]
"""

    TELEGRAM_PROMPT_TEMPLATE = """Summarize these {article_count} articles into a concise ~{max_words} word Telegram message with links.

Articles:
{articles_text}

Format your response EXACTLY as (use Markdown):

**Today's Highlights** - {date}

**Top Stories**
[2-3 sentences about the most significant story]
[Include link to the most relevant article]

**Key Developments**
[Brief coverage of other stories with links where relevant]

**Quick Hits**
{quick_hits_with_links}

Include article links in markdown format: [Title](url)
"""

    def __init__(self):
        """Initialize summarizer with OpenAI API."""
        self.config = get_config()

        if not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = AsyncOpenAI(api_key=self.config.openai_api_key)
        self.model = self.config.summary_model

    def _format_articles_for_prompt(self, articles: list[Article]) -> str:
        """Format articles into text for the prompt."""
        lines = []
        for i, article in enumerate(articles, 1):
            summary = article.summary or ""
            if len(summary) > 200:
                summary = summary[:200] + "..."
            lines.append(f"{i}. {article.title} ({article.source})")
            lines.append(f"   URL: {article.url}")
            if summary:
                lines.append(f"   Summary: {summary}")
            lines.append("")
        return "\n".join(lines)

    async def generate_epub_summary(self, articles: list[Article]) -> str | None:
        """Generate summary for EPUB (no links needed).

        Args:
            articles: List of articles to summarize

        Returns:
            Generated summary text, or None if failed
        """
        try:
            articles_text = self._format_articles_for_prompt(articles)

            prompt = self.EPUB_PROMPT_TEMPLATE.format(
                article_count=len(articles),
                max_words=self.config.summary_max_words,
                articles_text=articles_text,
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.7,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate EPUB summary: {e}")
            return None

    async def generate_telegram_summary(self, articles: list[Article]) -> str | None:
        """Generate summary for Telegram with links.

        Args:
            articles: List of articles to summarize

        Returns:
            Generated summary text with markdown links, or None if failed
        """
        try:
            articles_text = self._format_articles_for_prompt(articles)

            quick_hits = "\n".join([
                f"- [{a.title[:50]}...]({a.url})" if len(a.title) > 50
                else f"- [{a.title}]({a.url})"
                for a in articles[:5]
            ])

            prompt = self.TELEGRAM_PROMPT_TEMPLATE.format(
                article_count=len(articles),
                max_words=self.config.summary_max_words,
                articles_text=articles_text,
                date=datetime.now().strftime("%B %d, %Y"),
                quick_hits_with_links=quick_hits,
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.7,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to generate Telegram summary: {e}")
            return None


async def generate_summary(
    articles: list[Article],
    for_telegram: bool = False
) -> str | None:
    """Convenience function to generate summary.

    Args:
        articles: List of articles to summarize
        for_telegram: If True, includes links formatted for Telegram

    Returns:
        Generated summary text, or None if failed
    """
    config = get_config()

    if not config.summary_enabled:
        return None

    if not config.openai_api_key:
        logger.warning("OPENAI_API_KEY not set, skipping summary")
        return None

    summarizer = Summarizer()

    if for_telegram:
        return await summarizer.generate_telegram_summary(articles)
    else:
        return await summarizer.generate_epub_summary(articles)
