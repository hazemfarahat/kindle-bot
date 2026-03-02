"""HTML generation for Kindle-optimized web pages."""

import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import get_config
from .models import Article, SourceError


class WebBuilder:
    """Builds Kindle-optimized HTML pages from articles."""
    
    # CSS stylesheet optimized for Kindle e-ink browser
    STYLESHEET = """
    /* Kindle E-Ink Optimized Styles */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: Georgia, serif;
        font-size: 18px;
        line-height: 1.8;
        background: #fff;
        color: #000;
        padding: 1em;
        max-width: 100%;
    }
    
    /* Typography */
    h1 {
        font-size: 1.8em;
        margin: 0.5em 0;
        line-height: 1.2;
        border-bottom: 3px solid #000;
        padding-bottom: 0.3em;
    }
    
    h2 {
        font-size: 1.4em;
        margin: 1.2em 0 0.5em 0;
        line-height: 1.3;
    }
    
    h3 {
        font-size: 1.2em;
        margin: 1em 0 0.5em 0;
    }
    
    p {
        margin: 0.8em 0;
        text-align: justify;
    }
    
    a {
        color: #000;
        text-decoration: underline;
    }
    
    a:visited {
        color: #333;
    }
    
    /* Header */
    header {
        text-align: center;
        margin-bottom: 2em;
        border-bottom: 2px solid #000;
        padding-bottom: 1em;
    }
    
    header h1 {
        border: none;
        margin: 0.3em 0;
    }
    
    header .date {
        font-size: 1.2em;
        color: #333;
        margin: 0.5em 0;
    }
    
    header .count {
        font-size: 1em;
        color: #666;
        margin: 0.3em 0;
    }
    
    header nav {
        margin-top: 1em;
    }
    
    header nav a {
        display: inline-block;
        padding: 0.5em 1em;
        margin: 0.3em;
        border: 2px solid #000;
        text-decoration: none;
        font-weight: bold;
    }
    
    /* Table of Contents */
    .toc {
        background: #f5f5f5;
        padding: 1em;
        margin: 2em 0;
        border: 2px solid #000;
    }
    
    .toc h2 {
        margin-top: 0;
    }
    
    .toc ol {
        padding-left: 1.5em;
    }
    
    .toc li {
        margin: 0.8em 0;
        line-height: 1.4;
    }
    
    .toc a {
        font-weight: bold;
        font-size: 1.05em;
    }
    
    .toc-meta {
        font-size: 0.9em;
        color: #333;
        display: block;
        margin-top: 0.2em;
    }
    
    /* AI Summary Section */
    .ai-summary {
        background: #f9f9f9;
        padding: 1.5em;
        margin: 2em 0;
        border: 2px solid #000;
        border-left: 6px solid #000;
    }
    
    .ai-summary h2 {
        margin-top: 0;
    }
    
    .ai-summary strong {
        font-size: 1.1em;
        display: block;
        margin-top: 1em;
        margin-bottom: 0.3em;
    }
    
    .ai-disclaimer {
        font-size: 0.85em;
        color: #666;
        font-style: italic;
        margin-top: 1.5em;
        text-align: center;
        border-top: 1px solid #ccc;
        padding-top: 1em;
    }
    
    /* Article */
    article {
        margin: 3em 0;
        padding-top: 2em;
        border-top: 3px solid #000;
    }
    
    article:first-of-type {
        border-top: none;
    }
    
    .article-meta {
        font-size: 0.9em;
        color: #333;
        margin: 0.5em 0 1.5em 0;
        padding-bottom: 0.5em;
        border-bottom: 1px solid #ccc;
    }
    
    .source-badge {
        display: inline-block;
        background: #e0e0e0;
        padding: 0.2em 0.6em;
        border: 1px solid #999;
        font-weight: bold;
        margin-right: 0.5em;
    }
    
    .article-score {
        font-weight: bold;
    }
    
    .article-content {
        margin: 1.5em 0;
    }
    
    .article-content img {
        max-width: 100%;
        height: auto;
        margin: 1em 0;
        border: 1px solid #ccc;
    }
    
    .article-link {
        font-size: 0.9em;
        margin-top: 1.5em;
        padding-top: 1em;
        border-top: 1px solid #ccc;
        word-wrap: break-word;
    }
    
    .summary-only {
        background: #f5f5f5;
        padding: 1em;
        border-left: 4px solid #999;
        margin: 1em 0;
    }
    
    .summary-only em {
        color: #666;
    }
    
    /* Footer */
    footer {
        margin-top: 3em;
        padding-top: 1.5em;
        border-top: 2px solid #000;
        text-align: center;
        font-size: 0.9em;
        color: #666;
    }
    
    footer p {
        margin: 0.5em 0;
    }
    
    /* Archive Page */
    .archive-list {
        list-style-type: none;
        padding: 0;
    }
    
    .archive-item {
        margin: 1.5em 0;
        padding: 1em;
        border: 2px solid #000;
        background: #f9f9f9;
    }
    
    .archive-item a {
        font-size: 1.3em;
        font-weight: bold;
        text-decoration: none;
        display: block;
        margin-bottom: 0.5em;
    }
    
    .archive-item .meta {
        font-size: 0.9em;
        color: #666;
    }
    
    /* Errors Section */
    .errors-section {
        background: #f5f5f5;
        padding: 1em;
        border-left: 4px solid #666;
        margin: 2em 0;
        font-size: 0.9em;
    }
    
    .errors-title {
        color: #333;
        margin: 0 0 0.5em 0;
    }
    
    .errors-list {
        margin: 0;
        padding-left: 1.5em;
        color: #666;
    }
    
    /* Responsive adjustments */
    @media screen and (min-width: 600px) {
        body {
            max-width: 800px;
            margin: 0 auto;
            padding: 2em;
        }
    }
    """
    
    def __init__(self):
        """Initialize web builder."""
        self.config = get_config()
    
    def build(
        self,
        articles: list[Article],
        digest_type: str = "daily",
        errors: Optional[list[SourceError]] = None,
        output_dir: str = "docs",
        keep_days: int = 7,
        summary: Optional[str] = None,
    ) -> Path:
        """Build web pages from articles.
        
        Args:
            articles: List of articles to include
            digest_type: Type of digest ('daily', 'weekly', 'run-once')
            errors: List of source errors to include in footer
            output_dir: Base directory for web output
            keep_days: Number of days to keep in archive
            summary: AI-generated summary text
            
        Returns:
            Path to output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate date-based subdirectory for today's digest
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        digest_dir = output_path / date_str
        digest_dir.mkdir(parents=True, exist_ok=True)
        
        # Write CSS file (shared across all pages)
        css_path = output_path / "style.css"
        css_path.write_text(self.STYLESHEET, encoding="utf-8")
        
        # Build today's digest page
        self._build_digest_page(
            articles=articles,
            digest_type=digest_type,
            errors=errors,
            output_dir=digest_dir,
            date=now,
            summary=summary,
        )
        
        # Save JSON data for programmatic access
        self._save_json_data(articles, errors, digest_dir, now, digest_type)
        
        # Build archive index
        self._build_archive_index(output_path)
        
        # Build main index.html (redirect or link to latest)
        self._build_main_index(output_path, date_str, len(articles), now)
        
        # Cleanup old archives
        self._cleanup_old_archives(output_path, keep_days)
        
        return output_path
    
    def _build_digest_page(
        self,
        articles: list[Article],
        digest_type: str,
        errors: Optional[list[SourceError]],
        output_dir: Path,
        date: datetime,
        summary: Optional[str],
    ) -> None:
        """Build full digest page for a specific day."""
        # Generate title
        if digest_type == "weekly":
            from datetime import timedelta
            week_start = date - timedelta(days=date.weekday())
            week_end = week_start + timedelta(days=6)
            title = f"Tech Digest: {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
        else:
            title = f"Tech Digest: {date.strftime('%B %d, %Y')}"
        
        # Build TOC
        toc_html = self._build_toc_html(articles)
        
        # Build AI summary section
        summary_html = ""
        if summary:
            summary_html = self._build_summary_html(summary)
        
        # Build articles
        articles_html = ""
        for i, article in enumerate(articles, 1):
            articles_html += self._build_article_html(article, i)
        
        # Build errors section
        errors_html = ""
        if errors:
            errors_html = self._build_errors_html(errors)
        
        # Generate full HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{self._escape_html(title)}</title>
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header>
        <h1>Tech Digest</h1>
        <p class="date">{date.strftime('%A, %B %d, %Y')}</p>
        <p class="count">{len(articles)} Articles</p>
        <nav>
            <a href="../">Home</a>
            <a href="../archive/">Archive</a>
        </nav>
    </header>
    
    <main>
        {toc_html}
        {summary_html}
        {articles_html}
    </main>
    
    <footer>
        {errors_html}
        <p>Generated: {date.strftime('%B %d, %Y at %H:%M UTC')}</p>
        <p>Kindle News Digest</p>
    </footer>
</body>
</html>"""
        
        # Write file
        (output_dir / "index.html").write_text(html, encoding="utf-8")
    
    def _build_toc_html(self, articles: list[Article]) -> str:
        """Build table of contents HTML."""
        items_html = ""
        for i, article in enumerate(articles, 1):
            # Truncate long titles
            title = article.title
            if len(title) > self.config.epub_max_title_length:
                title = title[:self.config.epub_max_title_length - 3] + "..."
            
            # Build metadata
            meta_parts = []
            if self.config.epub_include_source_badge:
                meta_parts.append(article.source)
            if self.config.epub_include_score and article.raw_score > 0:
                meta_parts.append(f"{int(article.raw_score)} pts")
            
            meta = " - ".join(meta_parts)
            meta_html = f'<span class="toc-meta">{self._escape_html(meta)}</span>' if meta else ""
            
            items_html += f"""
            <li>
                <a href="#article-{i}">{self._escape_html(title)}</a>
                {meta_html}
            </li>
            """
        
        return f"""
        <section class="toc">
            <h2>Contents</h2>
            <ol>
                {items_html}
            </ol>
        </section>
        """
    
    def _build_summary_html(self, summary: str) -> str:
        """Build AI summary section HTML."""
        # Convert markdown-style formatting to HTML
        summary_html = summary
        summary_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', summary_html)
        summary_html = re.sub(r'\n\n', '</p><p>', summary_html)
        summary_html = re.sub(r'\n- ', '</p><p>• ', summary_html)
        summary_html = re.sub(r'\n', '<br/>', summary_html)
        summary_html = f'<p>{summary_html}</p>'
        
        return f"""
        <section class="ai-summary">
            <h2>Today's Highlights</h2>
            {summary_html}
            <div class="ai-disclaimer">
                This summary was generated by AI (GPT-4o-mini)
            </div>
        </section>
        """
    
    def _build_article_html(self, article: Article, index: int) -> str:
        """Build single article HTML."""
        # Article metadata
        meta_parts = []
        if self.config.epub_include_source_badge:
            meta_parts.append(f'<span class="source-badge">{self._escape_html(article.source)}</span>')
        if self.config.epub_include_score and article.raw_score > 0:
            meta_parts.append(f'<span class="article-score">{int(article.raw_score)} points</span>')
        if article.author:
            meta_parts.append(f'by {self._escape_html(article.author)}')
        if article.published:
            meta_parts.append(article.published.strftime('%B %d, %Y'))
        
        meta_html = ' • '.join(meta_parts)
        
        # Article content
        if article.is_summary_only:
            summary_text = article.summary if article.summary else "No summary available."
            content_html = f"""
            <div class="summary-only">
                <p><em>Full article not available - showing summary only.</em></p>
                <p>{self._escape_html(summary_text)}</p>
            </div>
            """
        else:
            content_html = article.full_content or article.summary or "<p>No content available.</p>"
        
        # Original link
        link_html = ""
        if self.config.epub_include_original_link:
            link_html = f"""
            <div class="article-link">
                <strong>Original:</strong> <a href="{self._escape_html(article.url)}">{self._escape_html(article.url)}</a>
            </div>
            """
        
        return f"""
        <article id="article-{index}">
            <h2>{self._escape_html(article.title)}</h2>
            <div class="article-meta">{meta_html}</div>
            <div class="article-content">
                {content_html}
            </div>
            {link_html}
        </article>
        """
    
    def _build_errors_html(self, errors: list[SourceError]) -> str:
        """Build errors section HTML."""
        error_items = "".join([
            f'<li><strong>{self._escape_html(e.source)}:</strong> {self._escape_html(e.error)}</li>'
            for e in errors
        ])
        
        return f"""
        <div class="errors-section">
            <h3 class="errors-title">Some sources were unavailable:</h3>
            <ul class="errors-list">
                {error_items}
            </ul>
        </div>
        """
    
    def _save_json_data(
        self,
        articles: list[Article],
        errors: Optional[list[SourceError]],
        output_dir: Path,
        date: datetime,
        digest_type: str,
    ) -> None:
        """Save digest data as JSON for programmatic access."""
        data = {
            "date": date.isoformat(),
            "digest_type": digest_type,
            "article_count": len(articles),
            "articles": [a.to_dict() for a in articles],
            "errors": [e.to_dict() for e in errors] if errors else [],
        }
        
        json_path = output_dir / "digest.json"
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def _build_archive_index(self, output_dir: Path) -> None:
        """Build archive index page listing all available digests."""
        archive_dir = output_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        # Find all digest directories (YYYY-MM-DD format)
        digest_dirs = []
        for item in output_dir.iterdir():
            if item.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', item.name):
                # Load JSON to get article count
                json_path = item / "digest.json"
                if json_path.exists():
                    try:
                        data = json.loads(json_path.read_text(encoding="utf-8"))
                        digest_dirs.append({
                            "date": datetime.fromisoformat(data["date"]),
                            "date_str": item.name,
                            "article_count": data["article_count"],
                        })
                    except (json.JSONDecodeError, KeyError):
                        pass
        
        # Sort by date (newest first)
        digest_dirs.sort(key=lambda x: x["date"], reverse=True)
        
        # Build archive items HTML
        if digest_dirs:
            items_html = ""
            for digest in digest_dirs:
                items_html += f"""
                <div class="archive-item">
                    <a href="../{digest['date_str']}/">{digest['date'].strftime('%A, %B %d, %Y')}</a>
                    <div class="meta">{digest['article_count']} articles</div>
                </div>
                """
        else:
            items_html = "<p>No archived digests available yet.</p>"
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Archive - Tech Digest</title>
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header>
        <h1>Digest Archive</h1>
        <nav>
            <a href="../">Home</a>
        </nav>
    </header>
    
    <main>
        <div class="archive-list">
            {items_html}
        </div>
    </main>
    
    <footer>
        <p>Kindle News Digest</p>
    </footer>
</body>
</html>"""
        
        (archive_dir / "index.html").write_text(html, encoding="utf-8")
    
    def _build_main_index(
        self,
        output_dir: Path,
        latest_date_str: str,
        article_count: int,
        date: datetime,
    ) -> None:
        """Build main index.html that links to latest digest."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="0; url={latest_date_str}/">
    <title>Tech Digest</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>Tech Digest</h1>
        <p class="date">{date.strftime('%A, %B %d, %Y')}</p>
        <p class="count">{article_count} Articles</p>
    </header>
    
    <main>
        <p>Redirecting to <a href="{latest_date_str}/">today's digest</a>...</p>
        <p><a href="archive/">View archive</a></p>
    </main>
    
    <footer>
        <p>Kindle News Digest</p>
    </footer>
</body>
</html>"""
        
        (output_dir / "index.html").write_text(html, encoding="utf-8")
    
    def _cleanup_old_archives(self, output_dir: Path, keep_days: int) -> None:
        """Remove digest directories older than keep_days."""
        if keep_days <= 0:
            return  # Don't clean up if keep_days is 0 or negative
        
        cutoff = datetime.now() - timedelta(days=keep_days)
        
        for item in output_dir.iterdir():
            if item.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', item.name):
                try:
                    dir_date = datetime.strptime(item.name, '%Y-%m-%d')
                    if dir_date < cutoff:
                        shutil.rmtree(item)
                except ValueError:
                    pass  # Skip directories that don't match date format
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )


def build_web(
    articles: list[Article],
    digest_type: str = "daily",
    errors: Optional[list[SourceError]] = None,
    output_dir: str = "docs",
    keep_days: int = 7,
    summary: Optional[str] = None,
) -> Path:
    """Convenience function to build web pages.
    
    Args:
        articles: Articles to include
        digest_type: Type of digest
        errors: Source errors
        output_dir: Output directory
        keep_days: Number of days to keep in archive
        summary: AI-generated summary
        
    Returns:
        Path to output directory
    """
    builder = WebBuilder()
    return builder.build(articles, digest_type, errors, output_dir, keep_days, summary)
