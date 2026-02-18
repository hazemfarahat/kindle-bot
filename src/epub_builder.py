"""EPUB generation with table of contents."""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ebooklib import epub

from .config import get_config
from .models import Article, SourceError


class EPUBBuilder:
    """Builds EPUB files from articles."""
    
    # CSS stylesheet for Kindle
    STYLESHEET = """
    body {
        font-family: Georgia, serif;
        line-height: 1.6;
        margin: 0;
        padding: 0;
    }
    
    h1 {
        font-size: 1.5em;
        margin-bottom: 0.5em;
        line-height: 1.2;
    }
    
    h2 {
        font-size: 1.3em;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }
    
    h3 {
        font-size: 1.1em;
        margin-top: 1em;
        margin-bottom: 0.5em;
    }
    
    p {
        margin: 0.8em 0;
        text-align: justify;
    }
    
    .article-meta {
        font-size: 0.85em;
        color: #666;
        margin-bottom: 1em;
        border-bottom: 1px solid #ddd;
        padding-bottom: 0.5em;
    }
    
    .source-badge {
        display: inline-block;
        background: #f0f0f0;
        padding: 2px 8px;
        border-radius: 3px;
        font-size: 0.85em;
    }
    
    .article-score {
        font-weight: bold;
    }
    
    .article-link {
        font-size: 0.85em;
        margin-top: 1.5em;
        padding-top: 0.5em;
        border-top: 1px solid #ddd;
    }
    
    .summary-only {
        background: #fff9e6;
        padding: 1em;
        border-left: 3px solid #f0ad4e;
        margin: 1em 0;
    }
    
    .summary-only em {
        color: #8a6d3b;
    }
    
    img {
        max-width: 100%;
        height: auto;
        margin: 1em 0;
    }
    
    .toc-title {
        font-size: 1.3em;
        margin-bottom: 1em;
    }
    
    .toc-list {
        list-style-type: none;
        padding: 0;
    }
    
    .toc-item {
        margin: 0.8em 0;
        padding-left: 1.5em;
        text-indent: -1.5em;
    }
    
    .toc-number {
        display: inline-block;
        width: 1.5em;
        font-weight: bold;
    }
    
    .toc-source {
        font-size: 0.85em;
        color: #666;
    }
    
    .cover-title {
        font-size: 2em;
        text-align: center;
        margin-top: 30%;
    }
    
    .cover-date {
        font-size: 1.2em;
        text-align: center;
        color: #666;
        margin-top: 1em;
    }
    
    .cover-count {
        font-size: 1em;
        text-align: center;
        color: #888;
        margin-top: 0.5em;
    }
    
    .errors-section {
        background: #fff3f3;
        padding: 1em;
        border-left: 3px solid #d9534f;
        margin: 2em 0 1em 0;
        font-size: 0.9em;
    }
    
    .errors-title {
        color: #a94442;
        margin: 0 0 0.5em 0;
    }
    
    .errors-list {
        margin: 0;
        padding-left: 1.5em;
        color: #666;
    }
    
    .colophon {
        font-size: 0.85em;
        color: #888;
        text-align: center;
        margin-top: 2em;
        padding-top: 1em;
        border-top: 1px solid #eee;
    }
    """
    
    def __init__(self):
        """Initialize EPUB builder."""
        self.config = get_config()
    
    def build(
        self,
        articles: list[Article],
        digest_type: str = "daily",
        errors: Optional[list[SourceError]] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """Build an EPUB from articles.
        
        Args:
            articles: List of articles to include
            digest_type: Type of digest ('daily', 'weekly', 'run-once')
            errors: List of source errors to include in footer
            output_path: Path to save EPUB (optional)
            
        Returns:
            Path to saved EPUB file
        """
        book = epub.EpubBook()
        
        # Generate title based on digest type
        now = datetime.now()
        if digest_type == "weekly":
            # Calculate week range
            from datetime import timedelta
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=6)
            title = self.config.epub_weekly_title_format.format(
                week_start=week_start.strftime("%b %d"),
                week_end=week_end.strftime("%b %d, %Y")
            )
        else:
            title = self.config.epub_title_format.format(
                date=now.strftime("%B %d, %Y")
            )
        
        # Set metadata
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(title)
        book.set_language(self.config.epub_language)
        book.add_author(self.config.epub_author)
        
        # Add CSS
        css = epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=self.STYLESHEET.encode("utf-8")
        )
        book.add_item(css)
        
        # Create chapters
        chapters = []
        spine = []
        
        # Cover page
        cover = self._create_cover(title, len(articles), now)
        book.add_item(cover)
        spine.append(cover)
        
        # Table of contents page (custom HTML TOC for reading)
        if self.config.epub_include_toc:
            toc_page = self._create_toc_page(articles)
            book.add_item(toc_page)
            spine.append(toc_page)
        
        # Article chapters
        article_chapters = []
        for i, article in enumerate(articles):
            chapter = self._create_article_chapter(article, i + 1)
            book.add_item(chapter)
            article_chapters.append(chapter)
            spine.append(chapter)
        
        # Errors/colophon page
        if errors:
            colophon = self._create_colophon(errors, now)
            book.add_item(colophon)
            spine.append(colophon)
        
        # Set table of contents for EPUB navigation (only article chapters)
        book.toc = article_chapters
        
        # Add NCX for EPUB2 compatibility (required by some readers)
        book.add_item(epub.EpubNcx())
        
        # Add Nav for EPUB3 but don't include in spine to avoid duplicate TOC
        nav = epub.EpubNav()
        book.add_item(nav)
        
        # Set spine - don't include 'nav' to avoid duplicate TOC display
        book.spine = spine
        
        # Generate output path
        if output_path is None:
            safe_title = re.sub(r'[^\w\s-]', '', title).strip()
            safe_title = re.sub(r'\s+', '_', safe_title)
            output_path = f"output/{safe_title}.epub"
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write EPUB
        epub.write_epub(output_path, book, {})
        
        return output_path
    
    def _create_cover(self, title: str, article_count: int, date: datetime) -> epub.EpubHtml:
        """Create cover page.
        
        Args:
            title: Book title
            article_count: Number of articles
            date: Generation date
            
        Returns:
            Cover chapter
        """
        content = f"""
        <html>
        <head>
            <title>Cover</title>
            <link rel="stylesheet" href="style/main.css"/>
        </head>
        <body>
            <div class="cover-title">{title}</div>
            <div class="cover-date">{date.strftime("%A, %B %d, %Y")}</div>
            <div class="cover-count">{article_count} Articles</div>
        </body>
        </html>
        """
        
        cover = epub.EpubHtml(
            title="Cover",
            file_name="cover.xhtml",
            content=content,
            lang=self.config.epub_language
        )
        cover.add_item(epub.EpubItem(uid="style", file_name="style/main.css", media_type="text/css"))
        
        return cover
    
    def _create_toc_page(self, articles: list[Article]) -> epub.EpubHtml:
        """Create custom table of contents page.
        
        Args:
            articles: List of articles
            
        Returns:
            TOC chapter
        """
        items_html = ""
        for i, article in enumerate(articles):
            # Truncate long titles
            title = article.title
            if len(title) > self.config.epub_max_title_length:
                title = title[:self.config.epub_max_title_length - 3] + "..."
            
            # Escape HTML
            title = self._escape_html(title)
            
            source_info = ""
            if self.config.epub_include_source_badge:
                source_info = f'<span class="toc-source">({article.source}'
                if self.config.epub_include_score and article.raw_score > 0:
                    source_info += f' - {int(article.raw_score)} pts'
                source_info += ')</span>'
            
            items_html += f"""
            <li class="toc-item">
                <span class="toc-number">{i + 1}.</span>
                <a href="article_{i + 1:02d}.xhtml">{title}</a>
                {source_info}
            </li>
            """
        
        content = f"""
        <html>
        <head>
            <title>Table of Contents</title>
            <link rel="stylesheet" href="style/main.css"/>
        </head>
        <body>
            <h1 class="toc-title">Contents</h1>
            <ol class="toc-list">
                {items_html}
            </ol>
        </body>
        </html>
        """
        
        toc = epub.EpubHtml(
            title="Table of Contents",
            file_name="toc.xhtml",
            content=content,
            lang=self.config.epub_language
        )
        
        return toc
    
    def _create_article_chapter(self, article: Article, index: int) -> epub.EpubHtml:
        """Create chapter for an article.
        
        Args:
            article: Article to create chapter for
            index: Article index (1-based)
            
        Returns:
            Article chapter
        """
        # Article metadata
        meta_html = ""
        if self.config.epub_include_source_badge:
            meta_html += f'<span class="source-badge">{article.source}</span> '
        if self.config.epub_include_score and article.raw_score > 0:
            meta_html += f'<span class="article-score">{int(article.raw_score)} points</span> '
        if article.author:
            meta_html += f'<span>by {self._escape_html(article.author)}</span> '
        if article.published:
            meta_html += f'<span>{article.published.strftime("%B %d, %Y")}</span>'
        
        # Article content
        content_html = article.full_content or article.summary or "No content available."
        
        # Summary indicator
        summary_indicator = ""
        if article.is_summary_only:
            summary_indicator = """
            <div class="summary-only">
                <p><em>Full article not available - showing summary only.</em></p>
            </div>
            """
        
        # Original link
        link_html = ""
        if self.config.epub_include_original_link:
            link_html = f"""
            <div class="article-link">
                <strong>Original:</strong> <a href="{article.url}">{article.url}</a>
            </div>
            """
        
        content = f"""
        <html>
        <head>
            <title>{self._escape_html(article.title)}</title>
            <link rel="stylesheet" href="style/main.css"/>
        </head>
        <body>
            <h1>{self._escape_html(article.title)}</h1>
            <div class="article-meta">
                {meta_html}
            </div>
            {summary_indicator}
            <div class="article-content">
                {content_html}
            </div>
            {link_html}
        </body>
        </html>
        """
        
        chapter = epub.EpubHtml(
            title=article.title[:50] + "..." if len(article.title) > 50 else article.title,
            file_name=f"article_{index:02d}.xhtml",
            content=content,
            lang=self.config.epub_language
        )
        
        return chapter
    
    def _create_colophon(self, errors: list[SourceError], date: datetime) -> epub.EpubHtml:
        """Create colophon page with errors and generation info.
        
        Args:
            errors: List of source errors
            date: Generation date
            
        Returns:
            Colophon chapter
        """
        errors_html = ""
        if errors:
            error_items = "".join([
                f'<li><strong>{e.source}:</strong> {self._escape_html(e.error)}</li>'
                for e in errors
            ])
            errors_html = f"""
            <div class="errors-section">
                <h3 class="errors-title">Some sources were unavailable:</h3>
                <ul class="errors-list">
                    {error_items}
                </ul>
            </div>
            """
        
        content = f"""
        <html>
        <head>
            <title>About This Digest</title>
            <link rel="stylesheet" href="style/main.css"/>
        </head>
        <body>
            {errors_html}
            <div class="colophon">
                <p>Generated on {date.strftime("%B %d, %Y at %H:%M UTC")}</p>
                <p>Kindle News Digest</p>
            </div>
        </body>
        </html>
        """
        
        colophon = epub.EpubHtml(
            title="About",
            file_name="colophon.xhtml",
            content=content,
            lang=self.config.epub_language
        )
        
        return colophon
    
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


def build_epub(
    articles: list[Article],
    digest_type: str = "daily",
    errors: Optional[list[SourceError]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Convenience function to build EPUB.
    
    Args:
        articles: Articles to include
        digest_type: Type of digest
        errors: Source errors
        output_path: Output path
        
    Returns:
        Path to EPUB file
    """
    builder = EPUBBuilder()
    return builder.build(articles, digest_type, errors, output_path)
