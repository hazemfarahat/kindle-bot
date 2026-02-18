# Kindle News Digest

Automatically collect top tech news from multiple sources and deliver them to your Kindle as an EPUB book.

## Features

- **7 News Sources**: Hacker News, Lobsters, Dev.to, TechCrunch, MIT Tech Review, TLDR, Techmeme
- **Smart Aggregation**: Deduplicates articles appearing across sources, boosts multi-source articles
- **Full Article Extraction**: Downloads complete articles with images (falls back to summaries for paywalled content)
- **Beautiful EPUBs**: Clean formatting with table of contents, source badges, and scores
- **Multiple Delivery Options**: Email to Kindle, Telegram bot, or both
- **Configurable Schedule**: Daily digest (morning) + Weekly "best of" (Saturday)
- **GitHub Actions**: Fully automated, runs in the cloud for free

## Quick Start

### 1. Create a Dedicated Gmail Account

1. Create a new Gmail account (e.g., `my-kindle-news@gmail.com`)
2. Enable 2-Factor Authentication
3. Create an App Password:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "Kindle News"
   - Copy the 16-character password

### 2. Subscribe to Newsletters

Subscribe to these newsletters using your new Gmail:
- **TLDR Tech**: https://tldr.tech/
- **Techmeme**: https://www.techmeme.com/ (Daily newsletter)

### 3. Configure Your Kindle

1. Find your Kindle email:
   - Go to https://www.amazon.com/hz/mycd/myx
   - Navigate to Preferences > Personal Document Settings
   - Find your `@kindle.com` address

2. Add sender to approved list:
   - In the same page, find "Approved Personal Document E-mail List"
   - Add your new Gmail address

### 4. Set Up Telegram Bot (Optional)

If you want to receive digests via Telegram instead of (or in addition to) email:

1. **Create a bot**:
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Send `/newbot` and follow the prompts
   - Copy the **Bot Token** (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Get your Chat ID**:
   - Start a chat with your new bot (send any message to it)
   - Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find your `chat_id` in the response (numeric value)

3. **Add to your environment**:
   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### 5. Set Up GitHub Repository

1. Fork this repository or push to your own GitHub
2. Go to Settings > Secrets and variables > Actions
3. Add these secrets:

| Secret | Description |
|--------|-------------|
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASSWORD` | Your 16-character App Password |
| `SENDER_EMAIL` | Same as SMTP_USER |
| `KINDLE_EMAIL` | Your `@kindle.com` address |
| `TELEGRAM_BOT_TOKEN` | (Optional) Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | (Optional) Your chat ID |

4. Enable GitHub Actions in the repository

### 6. Test It

1. Go to Actions tab
2. Select "Daily Tech Digest"
3. Click "Run workflow"
4. Choose "run-once" mode and your preferred delivery method
5. Check your Kindle or Telegram!

## Usage

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Run once (generate EPUB only, no delivery)
python -m src.main --run-once --delivery none

# Run once with email delivery (default)
python -m src.main --run-once

# Run once with Telegram delivery
python -m src.main --run-once --delivery telegram

# Run once with both email and Telegram
python -m src.main --run-once --delivery both

# Custom article count
python -m src.main --run-once --articles 15

# Custom output path
python -m src.main --run-once --output ~/Desktop/digest.epub
```

### Scheduled Runs (GitHub Actions)

The workflows run automatically:
- **Daily**: 6 AM Berlin time (5 AM UTC)
- **Weekly**: Saturday 7 AM Berlin time (6 AM UTC)

Manual triggers available in the Actions tab.

## Configuration

Edit `config.yaml` to customize:

### Sources

Enable/disable sources and adjust weights:

```yaml
sources:
  hackernews:
    enabled: true
    weight: 1.0      # Higher = more likely to appear in top 10
    max_fetch: 30    # How many articles to fetch
```

### Digest Settings

```yaml
digest:
  daily:
    enabled: true
    article_count: 10
  weekly:
    enabled: true
    article_count: 25
    day: saturday
```

### Content Extraction

```yaml
extraction:
  include_images: true
  max_images_per_article: 5
  max_image_width: 600
  paywall_fallback: "summary"  # or "skip"
```

### EPUB Formatting

```yaml
epub:
  title_format: "Tech Digest - {date}"
  include_toc: true
  include_source_badge: true
  include_original_link: true
```

### Delivery Options

```yaml
delivery:
  method: "email"  # Options: none, email, telegram, both
```

Override via CLI: `--delivery telegram`

## Project Structure

```
kindle-news/
├── src/
│   ├── main.py           # CLI entry point
│   ├── config.py         # Configuration loader
│   ├── models.py         # Data models
│   ├── aggregator.py     # Article aggregation & ranking
│   ├── extractor.py      # Content extraction
│   ├── epub_builder.py   # EPUB generation
│   ├── emailer.py        # Email sender
│   ├── telegram_sender.py # Telegram bot sender
│   ├── cache.py          # Weekly article cache
│   └── sources/
│       ├── base.py       # Base source class
│       ├── hackernews.py # Hacker News
│       ├── lobsters.py   # Lobsters
│       ├── devto.py      # Dev.to
│       ├── rss.py        # RSS feeds
│       └── newsletter.py # Newsletter parsing
├── config.yaml           # Configuration
├── requirements.txt      # Dependencies
└── .github/workflows/
    ├── daily.yml         # Daily digest workflow
    └── weekly.yml        # Weekly digest workflow
```

## Adding New Sources

1. Create a new file in `src/sources/`
2. Extend `BaseSource`:

```python
from .base import BaseSource
from ..models import Article, SourceType

class MySource(BaseSource):
    async def fetch(self) -> list[Article]:
        # Fetch and return articles
        pass
```

3. Register in `src/sources/__init__.py`
4. Add configuration in `config.yaml`

## Troubleshooting

### Email not sending

- Verify App Password is correct (16 characters, no spaces)
- Check that sender is in Kindle's approved list
- Try running with `--delivery none` first to verify digest generation

### Telegram not working

- Verify bot token is correct (from @BotFather)
- Ensure you've started a chat with your bot (sent at least one message)
- Check that chat ID is numeric and correct
- Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to verify

### No articles fetched

- Check internet connection
- Verify source URLs in config are accessible
- Check GitHub Actions logs for specific errors

### Images not loading

- Some sites block image downloads
- Try increasing `extraction.timeout_seconds`
- Images are optional - digest will work without them

### Newsletter sources empty

- Ensure newsletters are arriving in the dedicated inbox
- Check `sender_email` matches the actual sender
- Newsletters must be less than 36 hours old by default

## License

MIT License - feel free to modify and use as you wish.
