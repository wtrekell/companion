# Tools Directory - Current State Documentation

**Date:** 2025-10-30
**Purpose:** Pre-refactoring snapshot of tools/ directory structure, dependencies, and shared module architecture
**Context:** Consolidation effort to migrate from `tools/gmail/src/shared/` to `tools/_shared/`

---

## Executive Summary

The `tools/` directory contains **5 production-ready content collectors** totaling **11,148 lines of Python code**. A **shared utilities library** resides in `tools/gmail/src/shared/` (2,146 LOC) providing common functionality for config management, filtering, output, security, and state tracking.

**Key Finding:** Three tools (Gmail, Reddit, StackExchange) depend heavily on shared modules, while Web Articles has minimal dependency, and Transcribe is fully independent.

---

## Tool Inventory

| Tool | Status | LOC | Entry Points | Config File | State Storage |
|------|--------|-----|--------------|-------------|---------------|
| **Gmail** | ✅ Production | 5,561 | `gmail-collect`, `gmail-send` | `tools/gmail/settings/gmail.yaml` | JSON in `output/gmail/.gmail_state.json` |
| **Reddit** | ✅ Production | 878 | `reddit-collect` | `tools/reddit/settings/reddit.yaml` | JSON in `output/reddit/reddit_state.json` |
| **StackExchange** | ✅ Production | 1,085 | `stackexchange-collect` | `tools/stackexchange/settings/stackexchange.yaml` | SQLite in `output/stackexchange/stackexchange_state.db` |
| **Web Articles** | ✅ Production | 1,050 | `web-discover`, `web-fetch` | `tools/web_articles/settings/web-articles.yaml` | JSON in `tools/web_articles/data/gatherers_state.json` |
| **Transcribe** | ⚠️ Standalone | 2,573 | None (internal) | `tools/transcribe/settings/transcribe.yaml` | None |

**Total Code:** 11,148 LOC (excluding shared modules counted separately)

---

## Current Shared Module Location

### Physical Location
```
tools/gmail/src/shared/
├── __init__.py          (65 LOC)   - Public API exports
├── config.py            (201 LOC)  - YAML config with env var substitution
├── exceptions.py        (141 LOC)  - Exception hierarchy (11 types)
├── filters.py           (243 LOC)  - Content filtering with wildcards
├── http_client.py       (151 LOC)  - Rate-limited HTTP client
├── output.py            (300 LOC)  - Markdown generation with frontmatter
├── security.py          (523 LOC)  - SSRF protection, input sanitization
└── storage.py           (522 LOC)  - State management (JSON/SQLite)
```

**Total Shared LOC:** 2,146 lines

### Architecture Type
- **Single-source library** (no duplication, no symlinks)
- **Physical files** (not symbolic links)
- **Absolute imports** for cross-tool usage
- **Relative imports** for Gmail internal usage

---

## Import Dependency Matrix

### Tools Using Shared Modules

| Tool | Files Importing | Unique Imports | Dependency Level | Import Style |
|------|----------------|----------------|------------------|--------------|
| **Gmail** | 4 files | 7 items | Heavy | Relative (`from ...shared`) |
| **Reddit** | 3 files | 9 items | Heavy | Absolute (`from tools.gmail.src.shared`) |
| **StackExchange** | 3 files | 13 items | Very Heavy | Absolute (`from tools.gmail.src.shared`) |
| **Web Articles** | 1 file | 1 item | Minimal | Absolute (`from tools.gmail.src.shared`) |
| **Transcribe** | 0 files | 0 items | Independent | None |

### Module Usage Breakdown

| Shared Module | Gmail | Reddit | StackExchange | Web Articles | Total Tools |
|---------------|-------|--------|---------------|--------------|-------------|
| `config.py` | ✓ | ✓ | ✓ | ✓ | 4 |
| `exceptions.py` | ✓ | ✓ | ✓ | - | 3 |
| `filters.py` | ✓ | ✓ | ✓ | - | 3 |
| `output.py` | ✓ | ✓ | ✓ | - | 3 |
| `security.py` | ✓ | ✓ | ✓ | - | 3 |
| `storage.py` | ✓ | ✓ | ✓ | - | 3 |
| `http_client.py` | - | - | ✓ | - | 1 |

**Most critical modules:** `config.py` (used by all 4 dependent tools), `filters.py`, `output.py`, `storage.py` (used by 3 tools each)

---

## Detailed Import Analysis

### Gmail Tool (Relative Imports)

**Pattern:** Uses relative imports within same package
```python
from ...shared.config import load_yaml_config
from ...shared.exceptions import AuthenticationFailureError, ConfigurationValidationError
from ...shared.filters import apply_content_filter
from ...shared.output import ensure_folder_structure, write_markdown_file
from ...shared.security import sanitize_text_content, validate_email_address
from ...shared.storage import JsonStateManager
```

**Files importing shared:** 4
- `collector.py` - 7 imports
- `config.py` - 3 imports
- `auth.py` - 3 imports
- `send_cli.py` - 2 imports

---

### Reddit Tool (Absolute Imports)

**Pattern:** Uses absolute imports from Gmail's shared
```python
from tools.gmail.src.shared.config import get_env_var, load_yaml_config
from tools.gmail.src.shared.exceptions import StateManagementError
from tools.gmail.src.shared.filters import apply_content_filter
from tools.gmail.src.shared.output import ensure_folder_structure, update_existing_file, write_markdown_file
from tools.gmail.src.shared.security import sanitize_filename
from tools.gmail.src.shared.storage import JsonStateManager
```

**Files importing shared:** 3
- `collector.py` - 7 imports
- `config.py` - 2 imports
- `cli.py` - 1 import

**Critical Dependency:** Reddit is **completely dependent** on Gmail's shared modules for all utility functions.

---

### StackExchange Tool (Absolute Imports - Most Dependencies)

**Pattern:** Uses absolute imports from Gmail's shared
```python
from tools.gmail.src.shared.config import load_yaml_config
from tools.gmail.src.shared.exceptions import ConfigurationValidationError, ContentProcessingError, NetworkConnectionError, SSRFError
from tools.gmail.src.shared.filters import apply_content_filter
from tools.gmail.src.shared.http_client import RateLimitedHttpClient
from tools.gmail.src.shared.output import ensure_folder_structure, write_markdown_file
from tools.gmail.src.shared.security import sanitize_filename, sanitize_text_content, validate_url_for_ssrf, validate_input_length
from tools.gmail.src.shared.storage import SqliteStateManager
```

**Files importing shared:** 3
- `collector.py` - 10 imports (heaviest user)
- `config.py` - 4 imports
- `cli.py` - 4 imports

**Critical Dependency:** StackExchange uses **more shared modules than any other tool**, including security-critical SSRF protection.

---

### Web Articles Tool (Minimal Dependency)

**Pattern:** Uses only config loading
```python
from tools.gmail.src.shared.config import load_yaml_config
```

**Files importing shared:** 1
- `config.py` - 1 import

**Minimal Dependency:** Only uses YAML config loading, implements own fetching/filtering logic.

---

### Transcribe Tool (Independent)

**Pattern:** No shared module imports

**Status:** Completely independent with own implementations of:
- Configuration loading
- Security validation (SSRF, path traversal)
- Output handling

**Note:** Has comprehensive test coverage (4 test files, 1,193 LOC) but not integrated into main tools collection suite.

---

## Shared Module Deep Dive

### config.py (201 LOC)

**Purpose:** Secure YAML configuration loading with environment variable substitution and injection protection.

**Key Functions:**
- `load_yaml_config(configuration_file_path: str) -> dict[str, Any]`
- `get_env_var(environment_variable_key: str, default_value: str | None = None) -> str`

**Security Features:**
- Environment variable name validation (alphanumeric + underscore only)
- Nested `${VAR}` reference detection and prevention
- Recursion depth limit (max 5 levels)
- YAML injection character sanitization

**Used By:** Gmail (3 imports), Reddit (2 imports), StackExchange (1 import), Web Articles (1 import)

---

### exceptions.py (141 LOC)

**Purpose:** Standardized exception hierarchy for consistent error handling.

**Exception Classes (11 total):**

**Base:**
- `SignalCollectorError` - Base for all collector errors

**Operational:**
- `ConfigurationValidationError` - Config validation failures
- `AuthenticationFailureError` - Service authentication failures
- `RateLimitExceededError` - API rate limit hits (includes `retry_after_seconds`)
- `ContentProcessingError` - Content extraction/processing failures
- `StateManagementError` - State storage/retrieval failures
- `NetworkConnectionError` - Network operation failures

**Security:**
- `SecurityError` - Base for security-related errors
- `SSRFError` - SSRF attack attempts (includes `blocked_url`)
- `PathTraversalError` - Path traversal attempts (includes `attempted_path`)
- `InputValidationError` - Input validation failures (includes `field_name`, `invalid_input`)
- `ConfigurationInjectionError` - Configuration injection attempts

**Design Pattern:** All exceptions include optional `error_context: dict[str, Any]` for structured error information.

**Used By:** Gmail (7 types), Reddit (1 type), StackExchange (4 types)

---

### filters.py (243 LOC)

**Purpose:** Content filtering with keyword matching (wildcards supported), age filtering, and score thresholds.

**Key Functions:**
- `matches_keywords(text_content: str, keyword_list: list[str], case_sensitive: bool = False) -> bool`
- `apply_content_filter(content_data: dict[str, Any], filter_criteria: dict[str, Any]) -> bool`
- `strip_html_tags(html_content: str) -> str`

**Filter Criteria Supported:**
- `max_age_days` - Content age limit (timezone-aware datetime handling)
- `min_score` - Minimum score threshold (upvotes, etc.)
- `include_keywords` - Must match at least one (case-insensitive, wildcards)
- `exclude_keywords` - Must not match any (case-insensitive, wildcards)

**Wildcard Patterns:**
- `AI*` - Matches "AI", "AIops", "AI-powered"
- `*machine learning*` - Matches anywhere in text
- `claude?` - Matches "claude1", "claude2", "claudex"

**Used By:** Gmail (1 import), Reddit (1 import), StackExchange (1 import)

---

### http_client.py (151 LOC)

**Purpose:** Rate-limited HTTP client with retry logic and timeout handling.

**Key Class:**
```python
class RateLimitedHttpClient:
    def __init__(
        self,
        requests_per_second: float = 1.0,
        request_timeout_seconds: int = 30,
        maximum_retry_attempts: int = 3,
        backoff_factor: float = 1.0,
    )
```

**Features:**
- Sleep-based rate limiting (tracks last request timestamp)
- Automatic retry with exponential backoff
- Status code retry list: [429, 500, 502, 503, 504]
- Context manager support (`with` statement)
- Configurable timeout and retry attempts

**Used By:** StackExchange only (Reddit/Gmail use native API client rate limiting)

---

### output.py (300 LOC)

**Purpose:** Secure markdown file operations with YAML frontmatter, path traversal protection, and atomic writes.

**Key Functions:**
- `write_markdown_file(output_file_path: str, markdown_content: str, metadata_dict: dict[str, Any] | None = None) -> None`
- `ensure_folder_structure(output_directory: str, source_name: str, subsource_name: str | None = None) -> Path`
- `update_existing_file(existing_file_path: str, new_content: str) -> bool`

**Security Features:**
- Path traversal detection and prevention
- Symlink detection (optional allow/deny)
- Path component sanitization (removes `< > : " | ? *`)
- Windows reserved name handling (CON, PRN, AUX, etc.)
- Validates paths stay within allowed base directory

**Frontmatter Format:**
```markdown
---
source: "reddit"
collected_at: "2025-01-15T10:30:00Z"
score: 42
title: "Example Post"
---

# Post Content
Body text here...
```

**Used By:** Gmail (2 imports), Reddit (3 imports), StackExchange (2 imports)

---

### security.py (523 LOC)

**Purpose:** Multi-layered SSRF protection, input sanitization, and security validation.

**Key Functions:**
- `validate_url_for_ssrf(url: str, allow_private_ips: bool = False) -> bool`
- `sanitize_filename(filename: str, max_length: int = 255) -> str`
- `sanitize_text_content(content: str, max_length: int | None = None) -> str`
- `validate_email_address(email: str, field_name: str = "email") -> str`
- `validate_domain_name(domain: str) -> bool`
- `extract_domain_from_url(url: str) -> str | None`
- `validate_input_length(input_value: str, max_length: int, field_name: str = "input") -> str`

**SSRF Protection - Defense in Depth (5 Layers):**
1. **URL Scheme Validation:** Only `http` and `https` allowed
2. **Domain Blocklist:** Blocks `localhost`, `metadata.google.internal`, `169.254.169.254`
3. **Private IP Blocking:** RFC1918 ranges blocked by default
   - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
   - `127.0.0.0/8` (loopback)
   - `169.254.0.0/16` (link-local/APIPA)
   - IPv6 private ranges (`fc00::/7`, `fe80::/10`)
4. **Special IP Blocking:** Multicast (`224.0.0.0/4`), reserved addresses
5. **Hostname Validation:** DNS-compliant format (max 255 chars, valid charset)

**Documentation:** 89 lines of inline documentation explaining SSRF strategy, limitations (DNS rebinding, TOCTOU), and usage patterns.

**Used By:** Gmail (3 imports), Reddit (1 import), StackExchange (6 imports - heaviest security user)

---

### storage.py (522 LOC)

**Purpose:** State management with JSON (lightweight) or SQLite (high-volume) backends, featuring file locking for race condition prevention.

**Key Classes:**

**JsonStateManager:**
- `load_state() -> dict[str, Any]`
- `save_state(state_data: dict[str, Any]) -> None`
- `update_state(state_updates: dict[str, Any]) -> None`
- `batch_update_state(batch_updates: list[dict[str, Any]]) -> None`

**SqliteStateManager:**
- `is_item_processed(item_identifier: str) -> bool`
- `mark_item_processed(item_identifier: str, source_type: str, source_name: str, metadata_dict: dict[str, Any] | None = None) -> None`
- `get_processed_items(source_type: str | None = None, source_name: str | None = None, limit: int | None = None) -> list[...]`
- `cleanup_old_items(days_to_retain: int) -> int`

**File Locking Strategy (128 lines of documentation):**
- Uses POSIX `fcntl.flock` for exclusive locks
- Separate `.lock` file prevents corruption
- Non-blocking attempt first, falls back to 30s timeout
- Atomic writes via temp file + `fsync` + `rename`
- Prevents race conditions in read-modify-write operations

**SQLite Schema:**
```sql
CREATE TABLE processed_items (
    item_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    processed_timestamp TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_source_type ON processed_items(source_type);
CREATE INDEX idx_source_name ON processed_items(source_name);
```

**Used By:** Gmail (JsonStateManager), Reddit (JsonStateManager), StackExchange (SqliteStateManager)

---

### Public API (__init__.py - 65 LOC)

**Total Exports:** 38 items

**By Category:**
- **Config:** 2 exports (`get_env_var`, `load_yaml_config`)
- **Filters:** 2 exports (`apply_content_filter`, `matches_keywords`)
- **HTTP:** 1 export (`RateLimitedHttpClient`)
- **Output:** 3 exports (`ensure_folder_structure`, `update_existing_file`, `write_markdown_file`)
- **Security:** 7 exports (SSRF validation, sanitization, domain validation)
- **Exceptions:** 12 exports (complete exception hierarchy)
- **Storage:** 2 exports (`JsonStateManager`, `SqliteStateManager`)

---

## Configuration Patterns

### Common Structure Across All Tools

**Root-Relative Paths (no `./` prefix):**
```yaml
output_dir: "output/toolname"
state_file: "data/toolname_state.json"
```

**Environment Variable Substitution:**
```yaml
client_id: "${REDDIT_CLIENT_ID}"
api_key: "${STACKEXCHANGE_API_KEY}"
```

**Rate Limiting:**
```yaml
rate_limit_seconds: 2.0  # Seconds between requests
```

**Filter Criteria (Gmail, Reddit, StackExchange):**
```yaml
filters:
  max_age_days: 30
  min_score: 5
  include_keywords: ["AI", "machine learning"]
  exclude_keywords: ["spam", "promotional"]
```

### Tool-Specific Patterns

**Gmail - Rule-Based Actions:**
```yaml
rules:
  - name: "design-information"
    query: "subject:(design OR UX) is:unread"
    actions: ["save", "archive", "label:processed", "forward:team@example.com"]
    max_messages: 20
    save_attachments: false
```

**Reddit - Per-Subreddit Overrides:**
```yaml
default_filters:
  max_age_days: 21
  min_score: 5

subreddits:
  - name: "MachineLearning"
    max_posts: 50
    filters:
      min_score: 10  # Override default
```

**StackExchange - Tag-Based Filtering:**
```yaml
sites:
  - name: "stackoverflow"
    tags: ["python", "docker"]
    max_questions: 50
    include_answers: true
```

**Web Articles - Two-Stage Workflow:**
```yaml
review_file: "tools/web_articles/data/links_for_review.yaml"
sources:
  - url: "https://openai.com/news/"
    max_depth: 1
```

---

## Console Scripts and Entry Points

### From pyproject.toml

```toml
[project.scripts]
gmail-collect = "tools.gmail.src.collectors.gmail.cli:main"
gmail-send = "tools.gmail.src.collectors.gmail.send_cli:main"
reddit-collect = "tools.reddit.src.collectors.reddit.cli:main"
stackexchange-collect = "tools.stackexchange.src.collectors.stackexchange.cli:main"
web-discover = "tools.web_articles.src.collectors.web_articles.cli:discover"
web-fetch = "tools.web_articles.src.collectors.web_articles.cli:fetch"
```

**Total:** 6 commands across 4 tools (Transcribe has no console scripts)

### Common CLI Patterns

**Default Config Path:**
```python
@click.option(
    "--config",
    default="tools/toolname/settings/toolname.yaml",
)
```

**Common Flags:**
- `--dry-run` - Test mode, no file writes or API mutations
- `--verbose` - Debug-level logging
- `--config` - Override default config path

---

## Data Flow and Shared Module Usage

### Typical Collector Workflow

```
1. Load Config              → shared.config.load_yaml_config
2. Initialize Collector     → shared.storage.*StateManager
3. Fetch Content           → shared.http_client.RateLimitedHttpClient (StackExchange only)
4. Apply Filters           → shared.filters.apply_content_filter
5. Check State             → shared.storage.*StateManager.load_state / is_item_processed
6. Generate Output         → shared.output.ensure_folder_structure, write_markdown_file
7. Update State            → shared.storage.*StateManager.update_state / mark_item_processed
```

### State File Patterns

**Gmail State (JSON):**
```json
{
  "rules": {
    "design-information": {
      "last_run": "2025-01-15T10:30:00Z",
      "processed_count": 42
    }
  },
  "processed_messages": {
    "18a2f5b1c9d3e4f6": {
      "collected_at": "2025-01-15T10:30:00Z",
      "subject": "UX Design Trends"
    }
  }
}
```

**Reddit State (JSON):**
```json
{
  "t3_abc123": {
    "subreddit": "MachineLearning",
    "collected_at": "2025-01-15T10:30:00Z",
    "comment_count": 45,
    "score": 234
  }
}
```

**StackExchange State (SQLite):**
```
processed_items table:
- item_id: "12345678"
- source_type: "stackoverflow"
- source_name: "python"
- processed_timestamp: "2025-01-15T10:30:00Z"
- metadata_json: '{"score": 42, "answer_count": 3}'
```

---

## Current Issues and Inconsistencies

### Architectural Inconsistencies

**1. Import Pattern Inconsistency**
- **Gmail:** Relative imports (`from ...shared`)
- **Reddit, StackExchange:** Absolute imports (`from tools.gmail.src.shared`)
- **Impact:** Refactoring will require different changes for each tool

**2. State File Location Inconsistency**
- **Gmail:** `output/gmail/.gmail_state.json`
- **Reddit:** `output/reddit/reddit_state.json`
- **StackExchange:** `output/stackexchange/stackexchange_state.db`
- **Web Articles:** `tools/web_articles/data/gatherers_state.json`
- **Impact:** Inconsistent backup/restore procedures

**3. Data Directory Usage**
- **Gmail, Reddit, StackExchange:** No `data/` directories (use `output/` for state)
- **Web Articles:** Has `data/` directory with state and review files
- **Impact:** Confusing directory structure, unclear purpose of `data/` vs `output/`

---

### Testing Gaps

**Critical Gaps:**
1. **Shared modules (2,146 LOC)** - 0% test coverage
2. **Reddit collector (878 LOC)** - 0% test coverage
3. **StackExchange collector (1,085 LOC)** - 0% test coverage
4. **Web Articles (1,050 LOC)** - 0% test coverage
5. **Gmail collector logic** - Partial coverage (config only)

**Existing Tests:**
- **Gmail:** 1 test file (428 LOC) - `test_config.py` only
- **Transcribe:** 4 test files (1,193 LOC) - comprehensive coverage

**Risk Assessment:**
- **High Risk:** Changes to `security.py` (SSRF protection) untested
- **High Risk:** Changes to `storage.py` (file locking) untested
- **Medium Risk:** Changes to `filters.py` (keyword matching) untested
- **Medium Risk:** Integration between tools and shared modules untested

---

### Dependency Management

**1. Circular Dependency Risk**
- All tools depend on `tools.gmail.src.shared`
- Gmail tool code mixed with shared library
- **Impact:** Cannot extract shared library without restructuring

**2. Shared Module Versioning**
- No version number for shared modules
- No changelog for shared module changes
- No way to track which tool requires which shared module version
- **Impact:** Breaking changes to shared modules could break tools silently

---

## Statistics Summary

### Lines of Code
- **Total Tools LOC:** 11,148
- **Shared Modules LOC:** 2,146 (19.3% of total)
- **Tool-Specific LOC:** 9,002 (80.7% of total)
- **Test LOC:** 1,621 (14.5% of code + tests)

### Module Distribution
- **Gmail:** 5,561 LOC (49.9%) - includes shared modules
- **Transcribe:** 2,573 LOC (23.1%)
- **StackExchange:** 1,085 LOC (9.7%)
- **Web Articles:** 1,050 LOC (9.4%)
- **Reddit:** 878 LOC (7.9%)

### Shared Module Usage
- **Heavily Used (3 tools):** `config.py`, `filters.py`, `output.py`, `storage.py`, `exceptions.py`
- **Moderately Used (1 tool):** `http_client.py`, `security.py`
- **Unused Functions:** `is_safe_redirect_url`, `escape_markdown_special_chars`, `matches_keywords_debug`

### Import Statistics
- **Total import statements across tools:** 32 occurrences
- **Files importing from shared:** 11 unique files
- **Tools using shared modules:** 4 out of 5 (80%)
- **Most imported module:** `config.py` (used by all 4)
- **Most comprehensive user:** StackExchange (13 unique imports)

---

## File Tree (Complete Structure)

```
tools/
├── README.md (29,321 bytes)
├── INTEGRATION_GUIDE.md (10,176 bytes)
├── CLAUDE.md (13,157 bytes)
├── __init__.py (36 bytes)
│
├── gmail/ (5,561 LOC)
│   ├── src/
│   │   ├── collectors/gmail/
│   │   │   ├── cli.py (208 LOC)
│   │   │   ├── send_cli.py (398 LOC)
│   │   │   ├── collector.py (1,339 LOC)
│   │   │   ├── config.py (503 LOC)
│   │   │   ├── auth.py (303 LOC)
│   │   │   └── __init__.py (9 LOC)
│   │   └── shared/ *** CURRENT SHARED LIBRARY LOCATION ***
│   │       ├── __init__.py (65 LOC)
│   │       ├── config.py (201 LOC)
│   │       ├── exceptions.py (141 LOC)
│   │       ├── filters.py (243 LOC)
│   │       ├── http_client.py (151 LOC)
│   │       ├── output.py (300 LOC)
│   │       ├── security.py (523 LOC)
│   │       └── storage.py (522 LOC)
│   ├── settings/
│   │   └── gmail.yaml (131 lines)
│   └── tests/
│       ├── test_config.py (428 LOC)
│       └── conftest.py (223 LOC)
│
├── reddit/ (878 LOC)
│   ├── src/collectors/reddit/
│   │   ├── cli.py (224 LOC)
│   │   ├── collector.py (355 LOC)
│   │   ├── config.py (283 LOC)
│   │   └── __init__.py (16 LOC)
│   └── settings/
│       ├── reddit.yaml (79 lines)
│       └── reddit-design.yaml (variant)
│
├── stackexchange/ (1,085 LOC)
│   ├── src/collectors/stackexchange/
│   │   ├── cli.py (215 LOC)
│   │   ├── collector.py (590 LOC)
│   │   ├── config.py (279 LOC)
│   │   └── __init__.py (1 LOC)
│   └── settings/
│       ├── stackexchange.yaml (87 lines)
│       └── stackexchange-design.yaml (variant)
│
├── web_articles/ (1,050 LOC)
│   ├── src/collectors/web_articles/
│   │   ├── cli.py (224 LOC)
│   │   ├── collector.py (496 LOC)
│   │   ├── fetcher.py (221 LOC)
│   │   ├── config.py (105 LOC)
│   │   └── __init__.py (4 LOC)
│   ├── settings/
│   │   └── web-articles.yaml (85 lines)
│   └── data/
│       ├── gatherers_state.json (17,180 bytes)
│       └── links_for_review.yaml (2,118 bytes)
│
└── transcribe/ (2,573 LOC)
    ├── src/
    │   ├── cli.py (220 LOC)
    │   ├── transcriber.py (595 LOC)
    │   ├── config.py (392 LOC)
    │   ├── prompt_builder.py (173 LOC)
    │   └── __init__.py (0 LOC)
    ├── settings/
    │   └── transcribe.yaml
    └── tests/ (1,193 LOC)
        ├── test_transcriber.py (343 LOC)
        ├── test_security.py (192 LOC)
        ├── test_config.py (330 LOC)
        └── test_prompt_builder.py (328 LOC)
```

---

## Refactoring Considerations

### Phase 1: Extract Shared Library (Required)
1. Create `tools/_shared/` package
2. Move all modules from `tools/gmail/src/shared/` → `tools/_shared/`
3. Update 32 import statements across 11 files
4. Update Gmail to use absolute imports like other tools
5. Test all tools after migration

### Phase 2: Standardize Patterns (Recommended)
1. Standardize state file location (all in `output/toolname/`)
2. Clarify or remove `data/` directory usage
3. Document tool integration checklist
4. Add version number to shared library

### Phase 3: Add Test Coverage (High Priority)
1. Add tests for all shared modules (priority: security, storage, filters)
2. Add integration tests for each tool
3. Target 80%+ test coverage
4. Set up CI/CD pipeline

### Phase 4: Documentation (Ongoing)
1. Create shared module architecture diagram
2. Document data flow patterns
3. Create tool integration examples
4. Add troubleshooting guide

---

## Refactoring Impact Analysis

### Files Requiring Import Updates (32 imports across 11 files)

**Gmail (4 files - switch to absolute imports):**
- `tools/gmail/src/collectors/gmail/collector.py` (7 imports)
- `tools/gmail/src/collectors/gmail/config.py` (3 imports)
- `tools/gmail/src/collectors/gmail/auth.py` (3 imports)
- `tools/gmail/src/collectors/gmail/send_cli.py` (2 imports)

**Reddit (3 files - update path):**
- `tools/reddit/src/collectors/reddit/collector.py` (7 imports)
- `tools/reddit/src/collectors/reddit/config.py` (2 imports)
- `tools/reddit/src/collectors/reddit/cli.py` (1 import)

**StackExchange (3 files - update path):**
- `tools/stackexchange/src/collectors/stackexchange/collector.py` (10 imports)
- `tools/stackexchange/src/collectors/stackexchange/config.py` (4 imports)
- `tools/stackexchange/src/collectors/stackexchange/cli.py` (4 imports)

**Web Articles (1 file - update path):**
- `tools/web_articles/src/collectors/web_articles/config.py` (1 import)

### Testing Requirements After Refactoring
1. Run all existing tests (Gmail, Transcribe)
2. Test each console script manually
3. Verify state management still works
4. Verify config loading with env vars
5. Verify filter logic
6. Verify output generation

---

## Notes for Refactoring Team

1. **Preserve Git History:** Use `git mv` to maintain file history during move
2. **Batch Import Updates:** Can be done with find/replace, but verify each file
3. **Test Incrementally:** Test each tool after updating its imports
4. **Keep Shared Modules Intact:** Don't modify shared module logic during move
5. **Update Documentation:** Update all references to `tools/gmail/src/shared/` in docs
6. **Consider Versioning:** Add `__version__` to shared library after move

---

**End of Current State Documentation**
