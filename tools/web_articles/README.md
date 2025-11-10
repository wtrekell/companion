# Web Articles Collector

Production-ready web article discovery and collection tool using Firecrawl API.

## Overview

**Purpose**: Discover and collect web articles from configured sources (OpenAI, Anthropic, etc.) and save as markdown files with frontmatter.

**Status**: ✅ Production-ready

**Two-stage workflow**:
1. **Discovery** - Extract article links → generate `links_for_review.yaml` for human approval
2. **Fetch** - Download approved links → save as markdown with frontmatter

## Features

- ✅ JavaScript-rendered content support via Firecrawl V1 API
- ✅ Article link extraction with intelligent filtering
- ✅ State tracking to prevent duplicate discovery
- ✅ Human review workflow before content fetching
- ✅ Rate limiting and retry logic for API calls
- ✅ Markdown output with YAML frontmatter
- ✅ Global keyword exclusion filters
- ✅ Per-source configuration

## Installation

**From repository root:**

```bash
cd /Users/williamtrekell/Documents/durandal
uv sync
```

This installs the `web-discover` and `web-fetch` commands globally.

## Configuration

### Environment Variables

Add to `.env` file in repository root:

```bash
FIRECRAWL_API_KEY=fc-...
```

Get your API key from [firecrawl.dev](https://firecrawl.dev)

### Configuration File

Edit `tools/web_articles/settings/web-articles.yaml`:

```yaml
# Output directory (root-relative, no ./ prefix)
output_dir: "output/web-articles"

# State file path (automatically converted to .db for SQLite storage)
# The tool will use web_articles_state.db regardless of extension specified
state_file: "tools/web_articles/data/web_articles_state"

# Review file for human approval of discovered links
review_file: "tools/web_articles/data/links_for_review.yaml"

# Rate limit (seconds between requests)
rate_limit_seconds: 7.0

# Global exclude keywords (case-insensitive)
exclude_keywords:
  - legal
  - commercial-terms
  - politics
  - enterprise

# Source websites
sources:
  - url: "https://openai.com/news/"
    max_depth: 1
    keywords: []
    link_patterns:
      include: []
      exclude: []

  - url: "https://www.anthropic.com/news"
    max_depth: 1
    keywords: []

# Firecrawl settings
firecrawl:
  max_pages_per_source: 100
  timeout_ms: 30000
  only_main_content: true
```

## Usage

### Stage 1: Discovery

**Discover article links from all configured sources:**

```bash
cd /Users/williamtrekell/Documents/durandal
web-discover
```

**Options:**

```bash
web-discover --verbose             # Detailed progress output
web-discover --force               # Re-discover all links (ignore state)
web-discover --dry-run             # Validate config without running
web-discover --config path/to/config.yaml  # Custom config file
```

**Output:**

Creates a review file (default: `tools/web_articles/data/links_for_review.yaml`) with discovered links:

```yaml
file_metadata:
  generated_by: Link Review File Generator
  generated_on: '2025-10-22'
  total_sources: 3
  total_links: 37

sources:
- source_url: https://openai.com/news/
  discovery_date: '2025-10-22'
  notes: Links discovered from https://openai.com/news/ (37 new)
  links:
  - url: https://openai.com/index/sora-2/
    title: Sora 2
    matched_keywords: []
```

**Next steps:**
1. Review the generated review file (location shown in discovery output)
2. Delete or comment out unwanted links
3. Run Stage 2 (fetch)

### Stage 2: Fetch Content

**Fetch full article content from approved links:**

```bash
web-fetch
```

**Options:**

```bash
web-fetch --verbose                # Detailed progress output
web-fetch --dry-run                # Validate without fetching
web-fetch --config path/to/config.yaml  # Custom config file
```

**Output:**

Markdown files saved to `output/web-articles/` (output directory name configured in YAML):

```markdown
---
title: "Sora 2"
url: "https://openai.com/index/sora-2/"
source: "https://openai.com/news/"
created_date: null
collected_date: "2025-10-22T14:30:00.123456"
word_count: 1500
---

# Sora 2

[Article content as markdown...]
```

**File naming:** `YYYY-MM-DD-article-title.md`

**Frontmatter fields:**
- **title**: Article title extracted from link or URL
- **url**: Original article URL
- **source**: Source URL where the link was discovered
- **created_date**: Original publication date (set to `null` for scraped content, as this information is not reliably available)
- **collected_date**: ISO timestamp when the content was fetched (e.g., `2025-10-22T14:30:00.123456`)
- **word_count**: Number of words in the article content

The frontmatter follows the standardized naming convention used across all tools: `collected_date` (not `fetched_date`) for when content was gathered, and `created_date` for original publication date.

## State Management

**State database:** `tools/web_articles/data/web_articles_state.db` (SQLite)

Tracks all discovered URLs to prevent duplicate discovery on subsequent runs. The tool uses a shared SQLite-based state manager for structured querying and cleanup capabilities.

**Database schema:**
- **item_id**: Discovered URL (unique)
- **source_type**: Always "web_articles"
- **source_name**: Domain name extracted from URL (e.g., "openai.com")
- **processed_at**: ISO timestamp when URL was discovered
- Indexed on item_id and source_type for fast lookups

**Benefits of SQLite storage:**
- Structured queries by source or date range
- Concurrent-safe with proper locking
- Efficient indexed lookups for duplicate detection
- Easier cleanup and maintenance compared to JSON files

**Reset state:**

```bash
rm tools/web_articles/data/web_articles_state.db
```

Or use `--force` flag to bypass state for one run.

**Note:** The state database file (`.db`) is protected by `.gitignore` and will not be committed to version control. Each user maintains their own local state.

## Link Filtering

### Article Detection Patterns

**Included paths:**
- `/blog/`, `/news/`, `/post/`, `/article/`, `/index/`
- `/research/`, `/engineering/`, `/announcements/`
- `/updates/`, `/insights/`, `/stories/`
- Paths with year (e.g., `/2024/`, `/2025/`)

**Excluded paths:**
- `/tag/`, `/category/`, `/author/`, `/page/`
- `/search`, `/login`, `/signup`, `/privacy`, `/terms`
- `/about`, `/contact`, `/careers`
- File types: `.pdf`, `.jpg`, `.png`, `.gif`
- `/api/`, `/feed`, `/rss`

### Global Exclusion Keywords

Configure in `exclude_keywords` to filter out links by URL or title (case-insensitive):

```yaml
exclude_keywords:
  - legal
  - commercial-terms
  - politics
```

## Rate Limiting

**Default:** 7 seconds between requests (Firecrawl free tier: 10 requests/minute)

**Retry logic:**
- Detects 429 rate limit errors
- Automatically retries up to 3 times
- Exponential backoff with suggested wait time parsing

**Adjust rate limit:**

```yaml
rate_limit_seconds: 10.0  # More conservative
```

## Example Workflow

```bash
# Step 1: Discover links from configured sources
cd /Users/williamtrekell/Documents/durandal
web-discover --verbose

# Output:
# ✅ Review file created: links_for_review.yaml
# 📊 Processed 3 source(s)
# 🆕 New links: 37
# 💾 Total in state: 37

# Step 2: Review and edit links_for_review.yaml
# - Delete unwanted links
# - Comment out with # prefix

# Step 3: Fetch approved content
web-fetch --verbose

# Output:
# ✅ Successfully fetched: 35
# ❌ Failed: 0
# ⏭️  Skipped (too short): 2
# 📁 Articles saved to: output/web-articles
```

## Troubleshooting

### "FIRECRAWL_API_KEY not found"

Add to `.env` file in repository root:

```bash
FIRECRAWL_API_KEY=fc-your-key-here
```

### "Review file not found"

Run discovery first:

```bash
web-discover
```

### "Content too short"

Articles with less than 100 characters are skipped. This usually indicates:
- Paywall or login required
- Empty page or error page
- JavaScript-heavy content not rendered

### "Rate limit exceeded"

Increase `rate_limit_seconds` in config:

```yaml
rate_limit_seconds: 10.0
```

Or the tool will automatically retry with exponential backoff.

## Integration with Signal

This tool follows the Signal collector pattern used by `reddit-collect` and `stackexchange-collect`, with recent standardization updates.

**Similarities:**
- Root-level entry points in `pyproject.toml`
- YAML configuration with environment variable substitution
- State tracking for duplicate prevention
- Click CLI with `--dry-run`, `--verbose` flags
- Standardized frontmatter fields (`collected_date`, `created_date`)
- SQLite-based state management via shared `SqliteStateManager`

**Differences:**
- Two-stage workflow (discover → review → fetch) instead of single-stage
- Uses Firecrawl V1 API instead of PRAW/requests
- Direct tool calls (no CrewAI agents) for reliability

**Recent Standardization Updates:**
- Migrated from custom JSON state file (`gatherers_state.json`) to SQLite database (`web_articles_state.db`)
- Updated frontmatter: renamed `fetched_date` to `collected_date`, added `created_date` field
- Improved state management with indexed lookups and cleanup capabilities

## Architecture

```
tools/web_articles/
├── __init__.py
├── README.md (this file)
├── settings/
│   └── web-articles.yaml          # Configuration
├── data/
│   ├── web_articles_state.db      # SQLite state tracking
│   └── links_for_review.yaml      # Human review file (generated)
└── src/
    └── collectors/
        └── web_articles/
            ├── __init__.py
            ├── cli.py             # Click commands
            ├── config.py          # Configuration dataclasses
            ├── collector.py       # Discovery logic (uses SqliteStateManager)
            └── fetcher.py         # Fetch logic
```

## Dependencies

- `firecrawl-py>=1.0.0` - Firecrawl V1 API client
- `pyyaml>=6.0.1` - YAML configuration parsing
- `click>=8.1.7` - CLI framework
- `python-dotenv>=1.1.1` - Environment variable loading

## Known Limitations

1. **No image handling** - Images referenced in markdown are not downloaded
2. **Max depth not implemented** - Currently always depth=1 (single page crawl)
3. **No keyword filtering** - `keywords` field defined but not applied during filtering
4. **No incremental fetch** - Re-fetches all links in `links_for_review.yaml` each run

## Future Enhancements

- **Keyword filtering** - Apply `keywords` from sources.yaml
- **Incremental fetch mode** - Track fetched URLs, skip on re-run
- **Image extraction** - Download images referenced in markdown
- **Max depth crawling** - Follow links recursively up to configured depth
- **Better error handling** - Detailed error logs and recovery strategies
- **Duplicate detection** - Check for similar content before saving

## Contributing

When modifying this tool:

1. Follow the Signal collector pattern
2. Use type hints on all functions
3. Pass `mypy` strict mode
4. Run `ruff check --fix .` and `ruff format .`
5. Test with `--dry-run` before real runs
6. Update this README with changes

## License

Part of the Army of Me project. See root LICENSE file.
