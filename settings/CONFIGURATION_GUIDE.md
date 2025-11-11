# Configuration Guide

This guide covers configuration and filtering for all durandal tools.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration vs Filtering](#configuration-vs-filtering)
- [Universal Filter Criteria](#universal-filter-criteria)
- [Tool-Specific Guides](#tool-specific-guides)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

1. **Copy example settings** from this directory (e.g., `gmail.yaml`, `reddit.yaml`)
2. **Edit the YAML file** with your parameters
3. **Set environment variables** in `.env` file at project root
4. **Run the tool** - it will use `settings/{tool}.yaml` by default

**Custom config file:**
```bash
gmail-collect --config settings/my-custom-config.yaml
```

---

## Configuration vs Filtering

Understanding the distinction is crucial:

### Configuration Settings
**What they do:** Control WHAT data is collected and HOW

**Examples:**
- Gmail: `query` (Gmail search syntax), `max_messages`, `batch_size`
- Reddit: `sort_by` (hot/new/top), `include_comments`, `max_posts`
- StackExchange: `tags`, `sort_order`, `max_questions`
- Web Articles: `max_depth`, Firecrawl API settings
- Web Direct: `max_articles`, `rate_limit_seconds`, `timeout_seconds`
- PDF-to-MD: `max_pages`, `ocr_settings`, `image_dpi`
- Transcribe: `model` (tiny/medium/large), `language`, `temperature`

### Filter Criteria
**What they do:** Determine WHAT is kept after collection

**Examples:**
- `max_age_days`: Only keep content from last N days
- `include_keywords`: Must contain at least one keyword
- `exclude_keywords`: Must NOT contain any keyword
- `min_score`: Minimum score threshold (Reddit, StackExchange)

**Key Point:** Filters are applied AFTER data is collected/processed.

---

## Universal Filter Criteria

All 7 tools support these standardized filters:

### Age-Based Filtering

```yaml
filters:
  max_age_days: 30  # Only keep content from last 30 days
```

**How it works:**
- **Collectors** (Gmail, Reddit, StackExchange, Web Articles, Web Direct): Checks `created_date` (when content was originally published)
- **Processors** (PDF-to-MD, Transcribe): Checks file modification time

**Use cases:**
- Focus on recent content only
- Reduce processing time for large archives
- Stay current with fast-moving topics

### Keyword Filtering

```yaml
filters:
  include_keywords:
    - "AI"
    - "machine learning"
    - "deep*"        # Wildcard: matches "deep", "deeplearning", etc.
  exclude_keywords:
    - "spam"
    - "promotional"
    - "draft*"       # Wildcard: matches "draft", "drafts", etc.
```

**How it works:**
- **Case-insensitive** matching
- **Wildcards supported:** `*` (multiple chars), `?` (single char)
- **Searches:** title, text, body content
- **HTML stripping:** Automatically removes HTML tags before matching
- **Logic:** Must match at least ONE include keyword AND ZERO exclude keywords

**Use cases:**
- Topic-focused collections (e.g., only "python" posts)
- Spam filtering (exclude promotional content)
- Content curation (exclude "draft" or "test" content)

### Score-Based Filtering

```yaml
filters:
  min_score: 10  # Only keep content with score ≥ 10
```

**Availability:**
- ✅ Reddit (post score)
- ✅ StackExchange (question score)
- ❌ Gmail (N/A)
- ❌ Web Articles (N/A)
- ❌ Web Direct (N/A)
- ❌ PDF-to-MD (N/A)
- ❌ Transcribe (N/A)

**Use cases:**
- Quality filtering (high-scored content only)
- Popular content focus
- Reduce noise from low-engagement posts

### Content Length Filtering

```yaml
filters:
  min_content_length: 100  # Minimum word count
```

**Availability:**
- ✅ Web Direct (article word count)
- ❌ All other tools (N/A)

**Use cases:**
- Filter out stub pages or short navigation content
- Ensure articles meet minimum substance requirements
- Remove "coming soon" or placeholder pages

---

## Tool-Specific Guides

### Gmail Collector

**Configuration file:** `settings/gmail.yaml`

**Two-level filter cascade:**
1. **default_filters** - Apply to ALL rules
2. **rule.filters** - Apply to specific rule only

Filters from both levels UNION together (all keywords combined).

**Example:**
```yaml
# Global defaults
default_filters:
  max_age_days: 30
  include_keywords: ["urgent", "important"]
  exclude_keywords: ["spam", "promotional"]

# Per-rule configuration
rules:
  - name: "readwise-emails"
    query: "from:digest@readwise.io"
    save_attachments: false
    actions: ["save"]
    filters:
      include_keywords: ["highlights", "books"]  # Combined with defaults
```

**Result:** Email must contain `urgent` OR `important` OR `highlights` OR `books`, and must NOT contain `spam` OR `promotional`.

#### Gmail Label-Based Trigger Rules

Gmail supports **two types of rules**:
1. **Query rules** (above) - Automatic collection based on Gmail search queries
2. **Label rules** (NEW) - Manual triggering by applying labels to emails

**Label rules** enable on-demand processing: you manually apply a trigger label to any email, and the collector automatically performs configured actions when it detects that label.

**How It Works:**
```
You apply label "intake" → Collector detects it → Actions execute → Label removed (optional)
```

**Example Configuration:**
```yaml
# Label-based trigger rules (work alongside query rules)
label_rules:
  - name: "Intake Queue"
    trigger_label: "intake"           # Label to watch for
    actions: ["save", "archive"]      # Actions to perform
    remove_trigger: true              # Remove label after processing (default: true)
    max_messages: 50
    save_attachments: true
    filters:
      exclude_keywords: ["promotional"]

  - name: "Forward to Assistant"
    trigger_label: "for-assistant"
    actions: ["forward:assistant@example.com", "label:forwarded"]
    remove_trigger: true

  - name: "Important Archive"
    trigger_label: "archive-important"
    actions: ["save", "label:archived", "label:backup"]
    remove_trigger: true
    filters:
      max_age_days: 90
```

**Key Differences from Query Rules:**

| Feature | Query Rules | Label Rules |
|---------|-------------|-------------|
| **Triggering** | Automatic (Gmail search) | Manual (apply label) |
| **Control** | Configuration-based | User-initiated |
| **Processing** | Batch/scheduled | On-demand |
| **State Tracking** | By message ID | By label rule + message ID |
| **Use Case** | Automated monitoring | Manual curation |

**Label Rule Fields:**
- `name` - Descriptive name for the rule
- `trigger_label` - Gmail label to monitor (alphanumeric, dash, underscore, slash for nesting)
- `actions` - Same actions as query rules: `save`, `archive`, `label:name`, `forward:email`, etc.
- `remove_trigger` - Remove label after processing (default: true)
- `max_messages` - Limit per run (default: 50)
- `save_attachments` - Download attachments (default: true)
- `filters` - Content filtering (same as query rules)

**Label Naming:**
- **Allowed:** Letters, numbers, dash (`-`), underscore (`_`), slash (`/`)
- **Nesting:** Use `/` for folder-like structure: `actions/archive`, `queue/pending`
- **Case-insensitive:** Normalized to lowercase
- **Examples:** `intake`, `to-archive`, `process-later`, `actions/forward`

**Common Use Cases:**

1. **Manual Archive Queue:**
   ```yaml
   - name: "Archive Queue"
     trigger_label: "to-archive"
     actions: ["save", "archive"]
     remove_trigger: true
   ```
   *Apply "to-archive" label → Collector saves and archives → Label removed*

2. **Processing Queue (Keep Label):**
   ```yaml
   - name: "Processing Queue"
     trigger_label: "in-queue"
     actions: ["save", "label:processed"]
     remove_trigger: false  # Keep label for manual tracking
   ```
   *State prevents re-processing even when label remains*

3. **Conditional Forwarding:**
   ```yaml
   - name: "Forward to Team"
     trigger_label: "share-with-team"
     actions: ["forward:team@company.com", "label:shared"]
     remove_trigger: true
     filters:
       exclude_keywords: ["confidential", "private"]
   ```
   *Only forwards if content doesn't contain sensitive keywords*

**State Management:**
- Label rules and query rules track state separately
- Same email can be processed by both rule types independently
- State key format: `label_rule:{rule_name}:{message_id}`
- Prevents re-processing even if `remove_trigger: false`

**CLI Output:**
```
Collection completed:
  Query rules processed: 4
  Label rules processed: 2
  Total messages saved: 15
  Actions for 'readwise-emails': 5
  Actions for label rule 'Intake Queue': 8
  Trigger labels removed: 8
  ...
```

**See Also:** `settings/gmail-example.yaml` for complete configuration with 6 label rule examples.

**Required Environment Variables:**
```bash
# In .env file
GMAIL_CREDENTIALS_FILE=./data/gmail_credentials.json
GMAIL_TOKEN_FILE=./data/gmail_token.json
```

---

### Reddit Collector

**Configuration file:** `settings/reddit.yaml`

**Filters:** Single level (default_filters apply to all subreddits, or per-subreddit overrides)

**Example:**
```yaml
default_filters:
  max_age_days: 7
  min_score: 10
  include_keywords: ["python", "django", "flask"]
  exclude_keywords: ["beginner", "help"]

subreddits:
  - name: "python"
    sort_by: "top"
    include_comments: true
    max_posts: 50
    # Uses default_filters unless overridden
```

**Configuration vs Filtering:**
- `sort_by`: **Configuration** (tells Reddit API how to sort)
- `min_score`: **Filter** (keeps high-scored posts after collection)

**Required Environment Variables:**
```bash
# In .env file
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=durandal:v1.0.0 (by /u/yourusername)
```

---

### StackExchange Collector

**Configuration file:** `settings/stackexchange.yaml`

**Filters:** Supports standard filters PLUS tool-specific extensions:
- `min_answers`: Minimum number of answers required
- `required_tags`: Must have at least one tag from list
- `excluded_tags`: Must NOT have any tag from list

**Example:**
```yaml
default_filters:
  max_age_days: 90
  min_score: 5
  include_keywords: ["async", "await"]
  exclude_keywords: ["duplicate"]
  min_answers: 1              # StackExchange-specific
  required_tags: ["python"]   # StackExchange-specific
  excluded_tags: ["closed"]   # StackExchange-specific

sites:
  - name: "stackoverflow"
    tags: ["python", "asyncio"]  # Configuration: API query parameter
    sort_order: "votes"           # Configuration: API parameter
    max_questions: 100            # Configuration: pagination limit
```

**Configuration vs Filtering:**
- `tags` (in sites): **Configuration** (API query parameter)
- `required_tags` (in filters): **Filter** (post-collection filtering)

**Required Environment Variables:**
```bash
# In .env file
STACKEXCHANGE_API_KEY=your_api_key  # Optional but increases rate limits
```

---

### Web Articles Collector

**Configuration file:** `settings/web-articles.yaml`

**Two-stage workflow:**
1. **web-discover** - Find links, apply exclude_keywords
2. **Human review** - Edit `links_for_review.yaml`
3. **web-fetch** - Fetch approved links

**Example:**
```yaml
exclude_keywords:
  - "login"
  - "signup"
  - "cart"

sources:
  - url: "https://example.com"
    max_depth: 2
    keywords: ["tutorial", "guide"]  # Discovery: must match to include
```

**Note:** Web Articles uses exclude_keywords during discovery (different from other tools which filter after collection).

**Required Environment Variables:**
```bash
# In .env file
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

---

### Web Direct Collector

**Configuration file:** `settings/web-direct.yaml`

**Single-stage automated workflow:**
- Discovers article links from index pages using BeautifulSoup
- Fetches full content using trafilatura
- No human review step (fully automated)
- No API costs (uses free open-source libraries)

**Key Differences from Web Articles:**
- ✅ **No API costs** - Uses BeautifulSoup + trafilatura instead of Firecrawl
- ✅ **Automated** - Discover and fetch in single command
- ✅ **Filter support** - Full post-fetch filtering (age, keywords, content length)
- ❌ **Bot detection** - Some sites block crawlers (OpenAI, Perplexity return 403)
- ❌ **No human review** - Cannot manually curate before fetch

**Example:**
```yaml
output_dir: "output/web-direct"
state_file: "tools/web_direct/data/web_direct_state.json"
rate_limit_seconds: 1.0

# Global filters applied to all sources
default_filters:
  min_content_length: 100
  max_age_days: 30
  exclude_keywords:
    - "login"
    - "signup"

sources:
  - url: "https://www.anthropic.com/engineering"
    max_articles: 50
    # Source-specific filters (override defaults)
    filters:
      include_keywords: ["AI", "agents", "Claude"]

  - url: "https://ai.googleblog.com"
    max_articles: 25
```

**Filter Behavior:**
- **default_filters** - Apply to ALL sources unless overridden
- **source.filters** - Source-specific overrides
- Filters applied AFTER content extraction (not during discovery)
- Uses shared filters module (supports wildcards)

**Content Length Filtering:**
```yaml
default_filters:
  min_content_length: 100  # Minimum word count for articles
```

**State Management:**
- Tracks fetched articles to prevent re-fetching
- Tracks filtered articles to prevent re-evaluation
- Use `--force` flag to bypass state and re-fetch everything

**CLI Usage:**
```bash
# Basic usage (uses settings/web-direct.yaml)
web-direct

# Show detailed progress
web-direct --verbose

# Re-fetch all articles (bypass state)
web-direct --force

# Custom config file
web-direct --config settings/my-config.yaml

# Validate config without fetching
web-direct --dry-run
```

**Known Limitations:**
- **Bot detection:** Sites like OpenAI News and Perplexity Hub return 403 Forbidden
- **Dynamic content:** JavaScript-heavy sites may not render properly
- **Rate limits:** Aggressive crawling can trigger IP bans
- **No authentication:** Cannot access paywalled or login-required content

**Sites That Work Well:**
- ✅ Anthropic News & Engineering
- ✅ Google AI Blog
- ✅ Google Cloud AI/ML Blog
- ✅ Most WordPress/Ghost blogs
- ❌ OpenAI News (403 Forbidden)
- ❌ Perplexity Hub (403 Forbidden)

**Output:**
```
=== Web Direct Collection ===
Processing 6 source(s)...

  Fetched: Code execution with MCP: building more efficient AI agents...
  Fetched: Making Claude Code more secure and autonomous with sandboxing...
  Error processing source: 403 Client Error: Forbidden for url: https://openai.com/news/

=== Collection Complete ===
Sources processed: 5/6
Articles fetched: 15
Skipped (already fetched): 3
Output directory: output/web-direct

Tip: Use --force to re-fetch articles already in state
```

**When to Use Web Direct vs Web Articles:**

| Use Web Direct | Use Web Articles |
|----------------|------------------|
| Zero API costs | Budget for Firecrawl API |
| Automated workflow | Human curation needed |
| Sites allow crawlers | Sites block bots (OpenAI, etc) |
| High-volume collection | Low-volume, high-value content |
| Simple blog platforms | Complex JS-heavy sites |

**No environment variables required** (uses free libraries)

---

### PDF-to-MD Tool

**Configuration file:** `settings/pdf-to-md.yaml`

**Filters applied AFTER conversion** to determine which PDFs to keep.

**Example:**
```yaml
# Conversion settings (configuration)
max_pages: null        # Process all pages
ocr_all_pages: false   # Only OCR when needed
extract_images: true   # Save images
image_dpi: 96

# Content filters (applied after conversion)
filters:
  max_age_days: 30     # Only PDFs modified in last 30 days
  include_keywords:
    - "report"
    - "analysis*"
  exclude_keywords:
    - "draft"
    - "temp*"
```

**Configuration vs Filtering:**
- `max_pages`: **Configuration** (controls conversion process)
- `include_keywords`: **Filter** (determines which converted PDFs to keep)

**No environment variables required** (processes local files)

---

### Transcribe Tool

**Configuration file:** `settings/transcribe.yaml`

**Filters applied AFTER transcription** to determine which audio files to keep.

**Example:**
```yaml
# Transcription settings (configuration)
model: medium          # tiny, base, small, medium, large
language: en
temperature: 0

# Paragraph detection (configuration)
paragraph_detection:
  enabled: true
  pause_threshold: 2.0
  min_paragraph_chars: 100

# Content filters (applied after transcription)
filters:
  max_age_days: 7      # Only audio from last 7 days
  include_keywords:
    - "meeting"
    - "interview*"
  exclude_keywords:
    - "test"
    - "draft*"
```

**Configuration vs Filtering:**
- `model`: **Configuration** (controls transcription quality)
- `include_keywords`: **Filter** (determines which transcriptions to keep based on content)

**No environment variables required** (processes local files)

---

## Environment Variables

### .env File Location
Place `.env` file at project root: `/Users/williamtrekell/Documents/durandal/.env`

### Required by Tool

**Gmail:**
```bash
GMAIL_CREDENTIALS_FILE=./data/gmail_credentials.json
GMAIL_TOKEN_FILE=./data/gmail_token.json
```

**Reddit:**
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=durandal:v1.0.0 (by /u/yourusername)
```

**StackExchange:**
```bash
STACKEXCHANGE_API_KEY=your_api_key  # Optional but recommended
```

**Web Articles:**
```bash
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

**Web Direct, PDF-to-MD & Transcribe:**
- No environment variables required

### Variable Substitution in YAML

All YAML files support `${VAR}` syntax:

```yaml
token_file: ${GMAIL_TOKEN_FILE}
api_key: ${REDDIT_CLIENT_ID}
output_dir: ${HOME}/durandal-output  # Use system environment variables
```

---

## Troubleshooting

### Filters Not Working

**Problem:** Content not being filtered as expected

**Diagnosis:**
```yaml
# Add this temporarily to disable filters and test
filters:
  max_age_days: null
  include_keywords: []
  exclude_keywords: []
```

**Common Issues:**
1. **Wildcard syntax:** Use `*` (not `.*` or `%`)
2. **Case sensitivity:** Filters are case-insensitive (no need to worry)
3. **Empty lists:** `[]` means no filtering, not "filter everything"
4. **Date formats:** Tool handles various date formats automatically

### No Content Collected

**Check:**
1. **Configuration settings** - Is API query too restrictive?
2. **Environment variables** - Are credentials valid?
3. **Filter criteria** - Try disabling filters temporarily
4. **Rate limits** - Check tool logs for API errors

**Example Debug Workflow:**
```bash
# Step 1: Disable filters
filters: {}

# Step 2: Check if content is collected
# If yes → filters are too restrictive
# If no → configuration or credentials issue
```

### YAML Syntax Errors

**Common mistakes:**
```yaml
# ❌ WRONG: Missing quotes around special characters
include_keywords:
  - test*file

# ✅ CORRECT: Use quotes for wildcards
include_keywords:
  - "test*file"

# ❌ WRONG: Inconsistent indentation
filters:
max_age_days: 30
  include_keywords: []

# ✅ CORRECT: Consistent 2-space indentation
filters:
  max_age_days: 30
  include_keywords: []
```

**Validation:**
```bash
# Use yamllint or python to validate
python -c "import yaml; yaml.safe_load(open('settings/gmail.yaml'))"
```

### Filter Order of Operations

**All tools follow this pattern:**

1. **Collect/Process** data using configuration settings
2. **Apply age filter** (max_age_days) first
3. **Apply score filter** (min_score) if applicable
4. **Apply include_keywords** filter (must match at least one)
5. **Apply exclude_keywords** filter (must not match any)
6. **Apply tool-specific filters** (e.g., min_answers for StackExchange)
7. **Keep content** only if ALL filters pass

**Example:**
```yaml
filters:
  max_age_days: 30           # Step 1: Must be from last 30 days
  min_score: 10              # Step 2: Must have score ≥ 10
  include_keywords: ["AI"]   # Step 3: Must contain "AI"
  exclude_keywords: ["spam"] # Step 4: Must NOT contain "spam"
```

Content passes only if: recent AND high-scored AND contains "AI" AND doesn't contain "spam".

---

## Best Practices

### Start Broad, Then Narrow

```yaml
# Start with minimal filtering
filters:
  max_age_days: 30
  # No keyword filters yet

# After reviewing results, add keyword filters
filters:
  max_age_days: 30
  include_keywords: ["specific", "topics"]
```

### Use Wildcards Wisely

```yaml
# ✅ GOOD: Reasonable wildcards
include_keywords:
  - "python*"      # Matches: python, pythonic, python3
  - "machine?learning"  # Matches: machine-learning, machine_learning

# ❌ RISKY: Too broad
include_keywords:
  - "*"            # Matches everything (pointless)
  - "a*"           # Matches too many words
```

### Test Filters Incrementally

```bash
# 1. Run with no filters
# 2. Add age filter only
# 3. Add one include keyword
# 4. Add more keywords
# 5. Add exclude keywords last
```

### Document Your Filters

```yaml
filters:
  # Focus on recent high-quality Python content
  max_age_days: 7
  min_score: 20
  include_keywords:
    - "python"
    - "asyncio"
    - "performance"
  # Exclude beginner content and duplicates
  exclude_keywords:
    - "beginner"
    - "duplicate"
```

### Keep Configurations Organized

```bash
settings/
  gmail.yaml              # Main config
  gmail-work.yaml         # Work email account
  gmail-personal.yaml     # Personal account
  reddit-python.yaml      # Python subreddits only
  reddit-design.yaml      # Design subreddits
```

Then use `--config` flag:
```bash
gmail-collect --config settings/gmail-work.yaml
reddit-collect --config settings/reddit-python.yaml
```

---

## Additional Resources

- **Project README:** `/Users/williamtrekell/Documents/durandal/README.md`
- **Tool Updates:** `/Users/williamtrekell/Documents/durandal/tools/TOOL_UPDATES.md`
- **Tool-specific READMEs:** `/Users/williamtrekell/Documents/durandal/tools/{tool}/README.md`

## Support

For issues or questions:
1. Check tool-specific README for detailed documentation
2. Review TOOL_UPDATES.md for known issues
3. Verify YAML syntax with a validator
4. Test with minimal configuration first
