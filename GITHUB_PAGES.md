# GitHub Pages Web Digest

This project now includes a Kindle-optimized web version of the tech digest that's automatically deployed to GitHub Pages.

## Features

- **Kindle-optimized design**: High contrast black and white styling, large fonts, minimal CSS
- **Full article content**: Complete articles with extracted content, just like the EPUB version
- **AI summary**: "Today's Highlights" section with GPT-4o-mini generated summary
- **Rolling archive**: Keeps the last 7 days of digests accessible
- **Automatic deployment**: Updates daily alongside the EPUB generation

## URL Structure

```
https://[username].github.io/pushtokindle/
├── index.html              # Auto-redirects to latest digest
├── style.css               # Kindle-optimized stylesheet
├── archive/
│   └── index.html          # List of all available digests
├── 2026-03-02/
│   ├── index.html          # Full digest for March 2, 2026
│   └── digest.json         # JSON data (for programmatic access)
├── 2026-03-01/
│   ├── index.html
│   └── digest.json
└── ...
```

## Accessing on Kindle

### Option 1: Kindle's Experimental Browser
1. Open the Kindle web browser (Menu → Experimental Browser)
2. Navigate to: `https://[username].github.io/pushtokindle/`
3. Bookmark the page for easy access

### Option 2: QR Code
1. Generate a QR code for your GitHub Pages URL
2. Scan with a phone and text/email the link to access from other devices

## Local Testing

Generate web pages locally without running the full digest:

```bash
# Using the test script with cached articles
python test_web_builder.py

# Or as part of the full digest generation
python -m src.main --run-once --delivery none --build-web
```

The generated pages will be in the `docs/` directory.

## Manual CLI Usage

```bash
# Build web pages alongside EPUB generation
python -m src.main --run-once --build-web

# Custom archive duration (default is 7 days)
python -m src.main --run-once --build-web --web-keep-days 14

# Daily scheduled run (builds web automatically)
python -m src.main --type daily
```

## GitHub Pages Setup

### Initial Setup (One-time)

1. Go to your repository → Settings → Pages
2. Under "Source", select:
   - **Source**: Deploy from a branch
   - **Branch**: `main` (or `gh-pages`)
   - **Folder**: `/docs`
3. Click Save

The workflow will automatically deploy to GitHub Pages on every daily scheduled run or manual trigger.

### Workflow Configuration

The daily workflow (`.github/workflows/daily.yml`) has been updated to:

1. Generate the digest (EPUB + web pages)
2. Deploy the `docs/` directory to GitHub Pages using `peaceiris/actions-gh-pages@v4`
3. Keep only the last 7 days in the archive (configurable with `--web-keep-days`)

### Manual Workflow Trigger

When manually triggering the daily workflow, you can choose:
- **Build web pages**: Yes/No (default: Yes)
- **Archive duration**: Days to keep (default: 7)

## Archive Management

The web builder automatically cleans up old digests:
- Keeps the last N days (default: 7)
- Older digests are deleted to save space
- Archive index page shows all available digests

## JSON Data API

Each daily digest includes a `digest.json` file with structured data:

```json
{
  "date": "2026-03-02T14:30:00",
  "digest_type": "daily",
  "article_count": 10,
  "articles": [
    {
      "title": "Article Title",
      "url": "https://example.com/article",
      "source": "hackernews",
      "raw_score": 1184,
      "normalized_score": 776.76,
      "summary": "...",
      "full_content": "...",
      "author": "...",
      "published": "2026-03-01T12:00:00"
    }
  ],
  "errors": []
}
```

This enables:
- RSS feed generation
- Custom frontends
- Data analysis
- API integrations

## Kindle Browser Limitations

The Kindle's experimental browser has limitations:
- No JavaScript support (pages are pure HTML/CSS)
- Limited CSS support (uses basic layout only)
- Slow loading (optimized for minimal data)
- No image loading in some models (images are included but may not display)

The web design accounts for these limitations with:
- Pure HTML/CSS (no JavaScript)
- High contrast black and white
- Large, readable fonts
- Simple single-column layout
- Minimal external resources

## Troubleshooting

### Pages not updating
- Check the GitHub Actions workflow run for errors
- Verify GitHub Pages is enabled in repository settings
- Wait 2-3 minutes after workflow completes for deployment

### Kindle browser issues
- Clear browser cache: Settings → Applications → Experimental Browser → Clear Cache
- Try accessing on desktop first to verify pages work
- Check that images are small and optimized

### Archive not showing old digests
- Old digests are automatically deleted after N days (default: 7)
- Check the workflow logs to see if cleanup ran
- Adjust `--web-keep-days` parameter if you want to keep more history

## Future Enhancements

Possible improvements:
- [ ] RSS feed generation from JSON data
- [ ] Weekly digest compilation page
- [ ] Search functionality (static site search)
- [ ] Mobile-responsive improvements
- [ ] Dark mode toggle for non-Kindle browsers
- [ ] Article filtering by source
- [ ] Reading time estimates
