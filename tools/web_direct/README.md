# Web Direct Collector

Direct web content collector without API dependencies.

## Overview

**Purpose**: Fetch articles from exact URLs and save as markdown files with frontmatter. Uses trafilatura for content extraction, avoiding Firecrawl API costs.

**Status**: ✅ Production-ready

**Workflow**: Single-stage (fetch all configured URLs in one command)

## Features

- ✅ Fetch content from exact URLs specified in configuration
- ✅ Automatic content extraction using trafilatura
- ✅ State tracking to prevent duplicate fetches
- ✅ Retry logic with exponential backoff
- ✅ Rate limiting to avoid overwhelming servers
- ✅ Content filtering (keywords, age, length)
- ✅ Markdown output with YAML frontmatter
- ✅ Per-article or global filter configuration
- ✅ Secure filename generation

## Installation

**From repository root:**

```bash
cd /Users/williamtrekell/Documents/durandal
uv sync
```

This installs the `web-direct` command globally.

## Configuration

### Configuration File

Edit `settings/web-direct.yaml`:

```yaml
# Output directory (root-relative, no ./ prefix)
output_dir: "output/web-direct"

# State file path
state_file: "tools/web_direct/data/web_direct_state.json"

# Rate limit (seconds between requests)
rate_limit_seconds: 2.0

# Maximum retry attempts
max_retries: 3

# Request timeout (seconds)
timeout_seconds: 30

# Global filters (optional)
default_filters:
  max_age_days: 365
  min_content_length: 100
  exclude_keywords:
    - advertisement
    - sponsored

# Exact URLs to fetch
articles:
  - url: "https://anthropic.com/news/article"
    title: "Optional Title Override"

  - url: "https://openai.com/blog/article"
    filters:
      include_keywords: ["ai", "ml"]
```

## Usage

### Fetch All Configured Articles

```bash
cd /Users/williamtrekell/Documents/durandal
web-direct
```

### Options

```bash
web-direct --verbose              # Detailed progress output
web-direct --force                # Re-fetch even if already collected
web-direct --dry-run              # Validate config without fetching
web-direct --url "https://..."    # Fetch single URL (override config)
web-direct --config path/to/config.yaml  # Custom config file
```

### Output

Markdown files saved to `output/web-direct/`:

```markdown
---
title: "Article Title"
url: "https://example.com/article"
source: "web_direct"
created_date: "2025-01-15"
collected_date: "2025-11-04T14:30:00.123456"
word_count: 1500
author: "Author Name"
description: "Article description"
---

# Article Title

[Article content as markdown...]
```

**File naming:** `YYYY-MM-DD-article-title.md`

**Frontmatter fields:**
- **title**: Article title (extracted or from config override)
- **url**: Original article URL
- **source**: Always "web_direct"
- **created_date**: Original publication date (extracted by trafilatura)
- **collected_date**: ISO timestamp when content was fetched
- **word_count**: Number of words in article content
- **author**: Author name (if extracted by trafilatura)
- **description**: Article description (if extracted by trafilatura)

## State Management

**State file:** `tools/web_direct/data/web_direct_state.json` (JSON)

Tracks all fetched URLs to prevent duplicate collection on subsequent runs.

**State format:**
```json
{
  "https://example.com/article": {
    "collected_date": "2025-11-04T14:30:00",
    "word_count": 1500,
    "status": "success",
    "filename": "2025-11-04-article-title.md"
  }
}
```

**Reset state:**

```bash
rm tools/web_direct/data/web_direct_state.json
```

Or use `--force` flag to bypass state for one run.

**Note:** State file (`.json`) is protected by `.gitignore` and will not be committed to version control.

## Content Filtering

### Global Filters

Applied to all articles unless overridden:

```yaml
default_filters:
  max_age_days: 365          # Only content from last 365 days
  min_content_length: 100    # Minimum 100 words
  include_keywords: []       # Must contain at least one keyword
  exclude_keywords: []       # Must not contain these keywords
```

### Per-Article Filters

Override global filters for specific articles:

```yaml
articles:
  - url: "https://example.com/article"
    filters:
      max_age_days: 30
      include_keywords: ["ai", "machine learning"]
```

### Keyword Matching

- **Case-insensitive** by default
- **Wildcards**: `*` (multiple chars), `?` (single char)
- **Searches**: Title + content body

## Retry Behavior

Automatic retry with exponential backoff:

- **Max attempts**: 3 (configurable)
- **Backoff**: 2s, 4s, 8s
- **Retry on**: Network errors, timeouts, 5xx status codes, 429 rate limits
- **Skip on**: 4xx errors (except 429)

## Rate Limiting

**Default:** 2 seconds between requests

**Adjust rate limit:**

```yaml
rate_limit_seconds: 5.0  # More conservative
```

## Example Workflow

```bash
# Step 1: Add article URLs to settings/web-direct.yaml
# Edit the articles list with your target URLs

# Step 2: Fetch all configured articles
cd /Users/williamtrekell/Documents/durandal
web-direct --verbose

# Output:
# === Web Direct Collection ===
# Output directory: output/web-direct
# Total articles: 3
# Rate limit: 2.0s between requests
#
# [1/3] Processing: https://anthropic.com/news/article
#   ✅ Saved (1500 words)
# [2/3] Processing: https://openai.com/blog/article
#   ⏭️  Already in state, skipping
# [3/3] Processing: https://example.com/article
#   🚫 Filtered out
#
# === Collection Complete ===
# ✅ Successfully fetched: 1
# ⏭️  Skipped (already in state): 1
# 🚫 Filtered out: 1
# ❌ Failed: 0
# 📊 Total processed: 3
# 📁 Articles saved to: output/web-direct

# Step 3: Fetched articles are now in output/web-direct/
```

## Troubleshooting

### "Configuration file not found"

Make sure you're running from the repository root:

```bash
cd /Users/williamtrekell/Documents/durandal
web-direct
```

### "Failed to extract content from page"

Some pages may not work well with trafilatura:
- Pages with heavy JavaScript (no content in HTML)
- Paywalled content
- Login-required articles

Consider using `web_articles` tool (with Firecrawl) for these cases.

### "Security validation failed"

The tool blocks potentially unsafe URLs (localhost, private IPs, etc.) to prevent SSRF attacks. This is intentional security protection.

### Rate limit errors

Increase `rate_limit_seconds` in config:

```yaml
rate_limit_seconds: 5.0
```

Or use `max_retries` to increase retry attempts.

## Integration with Other Tools

This tool complements the existing tools ecosystem:

**Similarities with web_articles:**
- YAML configuration with environment variable substitution
- State tracking for duplicate prevention
- Click CLI with `--dry-run`, `--verbose` flags
- Standardized frontmatter fields
- JSON-based state management

**Key Differences from web_articles:**
- **Single-stage workflow**: No human review step
- **Exact URLs**: No link discovery or crawling
- **No API costs**: Uses trafilatura instead of Firecrawl
- **Simpler**: Designed for known articles, not exploration

**When to use web_direct:**
- ✅ You know exact article URLs to fetch
- ✅ Content is in static HTML (not heavy JavaScript)
- ✅ You want to avoid Firecrawl API costs
- ✅ Simple, straightforward content extraction

**When to use web_articles:**
- ✅ Need to discover articles from blog index pages
- ✅ Content requires JavaScript rendering
- ✅ Want human review before fetching
- ✅ Need sophisticated content extraction

## Architecture

```
tools/web_direct/
├── __init__.py
├── README.md (this file)
├── pyproject.toml          # Package definition
├── data/
│   └── web_direct_state.json  # State tracking (gitignored)
├── src/
│   └── collectors/
│       └── web_direct/
│           ├── __init__.py
│           ├── cli.py       # Click commands
│           ├── config.py    # Configuration dataclasses
│           └── collector.py # Collection logic
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_collector.py
```

## Dependencies

- `requests>=2.32.5` - HTTP client
- `trafilatura>=1.6.0` - HTML → Markdown conversion
- `click>=8.0.0` - CLI framework
- `python-dotenv>=1.2.1` - Environment variable loading
- `pyyaml>=6.0.3` - YAML configuration parsing

## Shared Module Integration

Uses shared utilities from `tools._shared`:
- **filters.py**: `apply_content_filter()` for keyword/age filtering
- **output.py**: `write_markdown_file()` for secure file writing
- **security.py**: `sanitize_filename()`, `validate_url_for_ssrf()`
- **storage.py**: `JsonStateManager` for state tracking
- **config.py**: `load_yaml_config()` for environment variable substitution

## Known Limitations

1. **No JavaScript rendering** - Won't work on pages that load content dynamically
2. **No link discovery** - Must provide exact URLs (not index pages)
3. **Basic metadata extraction** - trafilatura may miss some metadata fields
4. **No image downloading** - Images referenced in markdown are not saved locally

## Future Enhancements

- **RSS feed support** - Auto-fetch from RSS/Atom feeds
- **Sitemap parsing** - Extract URLs from sitemap.xml
- **Incremental updates** - Check for content changes and re-fetch
- **Parallel fetching** - Fetch multiple articles concurrently
- **Better metadata extraction** - More robust parsing for dates/authors

## Contributing

When modifying this tool:

1. Follow the collector pattern (consistent with reddit/stackexchange)
2. Use type hints on all functions
3. Pass `mypy` strict mode
4. Run `ruff check --fix .` and `ruff format .`
5. Test with `--dry-run` before real runs
6. Update this README with changes

## License

Part of the Durandal project. See root LICENSE file.
