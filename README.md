# Companion Tools

A collection of content gathering and processing utilities for research and analysis.

## Overview

This repository contains a suite of Python tools designed to collect, process, and organize content from various sources. The tools follow a consistent architecture with shared modules for filtering, state management, output formatting, and security.

## Tools

### Content Collectors

- **gmail** - Gmail collector with advanced filtering and automation capabilities
- **reddit** - Reddit post and comment collector with subreddit monitoring
- **stackexchange** - Stack Exchange question and answer collector
- **web_articles** - Web article collector using Firecrawl API (two-stage discover → fetch workflow)
- **web_direct** - Web article collector using free libraries (automated single-stage workflow)

### Content Processors

- **pdf-to-md** - PDF to Markdown conversion utility
- **transcribe** - Audio transcription utility

## Architecture

### Shared Modules (`tools/_shared/`)

All tools leverage common functionality from shared modules:

- **config.py** - Configuration management with environment variable substitution
- **exceptions.py** - Centralized exception hierarchy for consistent error handling
- **filters.py** - Content filtering by keywords, age, and metadata scores
- **http_client.py** - HTTP client with rate limiting and automatic retry
- **output.py** - Secure markdown operations with frontmatter and path validation
- **security.py** - Filesystem safety utilities (filename sanitization, URL validation)
- **storage.py** - State management for tracking processed content

### Configuration

All tool settings are centralized in the `settings/` directory:

- Each tool has a corresponding `.yaml` configuration file
- Settings include API credentials, filtering criteria, and tool-specific options
- Template files (`.yaml.template`) provided for easy setup

## Requirements

- **Python**: 3.12+
- **Package Manager**: uv
- **Type Hints**: Required for all function definitions

## Installation

```bash
# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

## Usage

Each tool can be run independently. See individual tool READMEs in `tools/<tool-name>/` for specific usage instructions.

### Common Patterns

**Gmail Collector:**
```bash
cd tools/gmail
uv run python -m collectors.gmail.collector
```

**Reddit Collector:**
```bash
cd tools/reddit
uv run python -m collectors.reddit.collector
```

**Web Articles Discovery & Fetch:**
```bash
cd tools/web_articles
uv run web-discover
# Review generated links_for_review.yaml
uv run web-fetch
```

**PDF to Markdown:**
```bash
cd tools/pdf-to-md
uv run python pdf_to_md.py --input-dir <pdf-dir> --output-dir <output-dir>
```

## Code Quality

The project maintains high code quality standards:

- **ruff**: Modern Python linter and formatter (line length: 120 characters)
- **mypy**: Static type checking with strict configuration
- **pytest**: Comprehensive test coverage for collectors

```bash
# Run linter and formatter
uv run ruff check .
uv run ruff format .

# Run type checker
uv run mypy .

# Run tests
uv run pytest
```

## Features

### Standardized Frontmatter

All tools generate markdown output with consistent YAML frontmatter:

**Universal Fields (Tier 1):**
- `title` - Content title or derived filename
- `source` - Origin identifier
- `created_date` - Original content creation timestamp (ISO 8601)
- `collected_date` - Collection/processing timestamp (ISO 8601)
- `url` - Source URL when applicable

**Tool-Specific Fields:**
Each tool adds relevant metadata (author, score, tags, etc.)

### Content Filtering

Configurable filtering across all collectors:

- `max_age_days` - Filter content older than N days
- `min_score` - Minimum score threshold (where applicable)
- `include_keywords` - Require at least one match (supports wildcards `*` and `?`)
- `exclude_keywords` - Disqualify content if any match

### State Management

- **JsonStateManager** - Simple JSON file storage for basic duplicate prevention (Gmail, Reddit)
- **SqliteStateManager** - Structured SQLite storage with indexing and cleanup (StackExchange, Web Articles)

## Documentation

See `tools/TOOL_UPDATES.md` for:
- Detailed feature implementation status
- Shared module usage patterns
- Configuration vs filter criteria distinction
- Code quality assessment and improvement roadmap

## Contributing

This project follows these conventions:

1. All code must include type hints
2. Follow the established shared module patterns
3. Maintain test coverage for new features
4. Use descriptive variable names
5. Document configuration options in tool READMEs

## License

[Add your license information here]
