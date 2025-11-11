"""Web direct content collector.

This module collects web content by discovering article links from index pages
and extracting content using trafilatura.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tools._shared.filters import apply_content_filter
from tools._shared.output import write_markdown_file
from tools._shared.security import sanitize_filename, validate_url_for_ssrf
from tools._shared.storage import JsonStateManager

from .config import FilterCriteria, SourceConfig, WebDirectConfig


class WebDirectCollector:
    """Collects web content by discovering and fetching articles from index pages."""

    def __init__(self, config: WebDirectConfig):
        """Initialize the collector.

        Args:
            config: Web direct configuration

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config

        # Initialize state manager
        self.state_file = Path(self.config.state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_manager = JsonStateManager(str(self.state_file))
        self.state: dict[str, dict[str, Any]] = self.state_manager.load_state()

        # Initialize HTTP session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=2,  # 2s, 4s, 8s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set user agent
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; WebDirectCollector/0.1.0; +https://github.com)",
            }
        )

    def collect(self, force: bool = False, verbose: bool = False) -> dict[str, Any]:
        """Collect content from all configured sources.

        Args:
            force: If True, re-fetch even if already in state
            verbose: If True, print detailed progress information

        Returns:
            Dictionary with collection statistics
        """
        # Always show basic start message
        print("\n=== Web Direct Collection ===")
        print(f"Processing {len(self.config.sources)} source(s)...\n")

        if verbose:
            print(f"Output directory: {self.config.output_dir}")
            print(f"Rate limit: {self.config.rate_limit_seconds}s between requests\n")

        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

        # Collection statistics
        stats = {
            "sources_processed": 0,
            "links_discovered": 0,
            "articles_fetched": 0,
            "skipped_already_fetched": 0,
            "skipped_previously_filtered": 0,
            "articles_failed": 0,
            "articles_filtered": 0,
        }

        # Process each source
        for idx, source in enumerate(self.config.sources, 1):
            if verbose:
                print(f"\n[{idx}/{len(self.config.sources)}] Processing source: {source.url}")

            try:
                # Discover article links from index page
                links = self._discover_links(source.url, verbose)

                if verbose:
                    print(f"  Found {len(links)} potential article links")

                stats["links_discovered"] += len(links)

                # Limit to max_articles
                if len(links) > source.max_articles:
                    if verbose:
                        print(f"  Limiting to {source.max_articles} articles (max_articles setting)")
                    links = links[: source.max_articles]

                # Fetch each article
                for link_idx, article_url in enumerate(links, 1):
                    if verbose:
                        print(f"  [{link_idx}/{len(links)}] {article_url}")

                    # Check if already processed
                    if not force and article_url in self.state:
                        state_entry = self.state[article_url]
                        status = state_entry.get("status", "unknown")

                        if status == "filtered":
                            if verbose:
                                reason = state_entry.get("filter_reason", "unknown")
                                print(f"    Previously filtered ({reason}), skipping")
                            stats["skipped_previously_filtered"] += 1
                        else:
                            if verbose:
                                print("    Already fetched, skipping")
                            stats["skipped_already_fetched"] += 1
                        continue

                    # Fetch and process article
                    try:
                        result = self._fetch_article(article_url, source, verbose)

                        # Check if filtered out (returns tuple of (None, reason))
                        if isinstance(result, tuple) and result[0] is None:
                            filter_reason = result[1]
                            # Add to state to prevent re-processing
                            self.state[article_url] = {
                                "filtered_date": datetime.now().isoformat(),
                                "status": "filtered",
                                "filter_reason": filter_reason,
                            }
                            stats["articles_filtered"] += 1
                            if verbose:
                                print(f"    Filtered out ({filter_reason})")
                            continue

                        # Save article
                        self._save_article(article_url, result, verbose)
                        stats["articles_fetched"] += 1

                        if verbose:
                            print(f"    Saved ({result['word_count']} words)")
                        else:
                            # Always show successful fetches
                            print(f"  Fetched: {result['title'][:60]}...")

                    except Exception as e:
                        if verbose:
                            print(f"    Error: {e}")
                        stats["articles_failed"] += 1
                        continue

                    # Rate limiting
                    if link_idx < len(links):
                        time.sleep(self.config.rate_limit_seconds)

                stats["sources_processed"] += 1

            except Exception as e:
                print(f"  Error processing source: {e}")
                continue

        # Save state
        self.state_manager.save_state(self.state)

        # Always show summary
        print("\n=== Collection Complete ===")
        print(f"Sources processed: {stats['sources_processed']}/{len(self.config.sources)}")
        print(f"Articles fetched: {stats['articles_fetched']}")

        # Show skip counts to explain why nothing was fetched
        if stats['skipped_already_fetched'] > 0:
            print(f"Skipped (already fetched): {stats['skipped_already_fetched']}")
        if stats['skipped_previously_filtered'] > 0:
            print(f"Skipped (previously filtered): {stats['skipped_previously_filtered']}")

        if verbose:
            print(f"Links discovered: {stats['links_discovered']}")
            print(f"Articles filtered (this run): {stats['articles_filtered']}")
            print(f"Articles failed: {stats['articles_failed']}")

        print(f"Output directory: {self.config.output_dir}")

        # Helpful tip if nothing was fetched due to state
        if stats['articles_fetched'] == 0 and stats['skipped_already_fetched'] > 0:
            print("\nTip: Use --force to re-fetch articles already in state\n")
        else:
            print()

        return stats

    def _discover_links(self, source_url: str, verbose: bool = False) -> list[str]:
        """Discover article links from an index page.

        Args:
            source_url: URL of index/blog page to scrape
            verbose: If True, print progress

        Returns:
            List of discovered article URLs

        Raises:
            requests.RequestException: If HTTP request fails
        """
        # Fetch the index page
        response = self.session.get(source_url, timeout=self.config.timeout_seconds)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract all links
        all_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            # Skip anchors and javascript
            if href.startswith("#") or href.startswith("javascript:"):
                continue

            # Convert relative URLs to absolute
            absolute_url = urljoin(source_url, href)

            # Validate URL
            parsed = urlparse(absolute_url)
            if not parsed.scheme or not parsed.netloc:
                continue

            all_links.append(absolute_url)

        # Filter to article-like links
        article_links = self._filter_article_links(all_links, source_url)

        # Remove duplicates
        unique_links = list(dict.fromkeys(article_links))

        return unique_links

    def _filter_article_links(self, links: list[str], base_url: str) -> list[str]:
        """Filter links to only include article-like content.

        Args:
            links: List of URLs to filter
            base_url: Base URL to filter against

        Returns:
            Filtered list of article-like URLs
        """
        filtered = []
        base_domain = urlparse(base_url).netloc

        for url in links:
            parsed = urlparse(url)

            # Only keep links from the same domain
            if parsed.netloc != base_domain:
                continue

            path_lower = parsed.path.lower()

            # Skip common non-article paths
            skip_patterns = [
                "/tag/",
                "/tags/",
                "/category/",
                "/categories/",
                "/author/",
                "/authors/",
                "/page/",
                "/search",
                "/login",
                "/signup",
                "/register",
                "/privacy",
                "/terms",
                "/about",
                "/contact",
                "/careers",
                ".pdf",
                ".jpg",
                ".png",
                ".gif",
                "/api/",
                "/feed",
                "/rss",
            ]

            if any(pattern in path_lower for pattern in skip_patterns):
                continue

            # Prefer paths that look like articles
            article_indicators = [
                "/blog/",
                "/news/",
                "/post/",
                "/article/",
                "/index/",
                "/research/",
                "/engineering/",
                "/announcements/",
                "/updates/",
                "/insights/",
                "/stories/",
                r"/\d{4}/",  # Year in path
            ]

            # Check if it has article indicators
            has_indicator = any(re.search(pattern, path_lower) for pattern in article_indicators)

            # Also include if the base URL is a news/blog/engineering page and this is a subpage
            base_path = urlparse(base_url).path.lower()
            is_from_news_page = any(x in base_path for x in ["/news", "/blog", "/engineering"])
            is_subpage = len(parsed.path.strip("/").split("/")) >= 2

            if has_indicator or (is_from_news_page and is_subpage):
                filtered.append(url)

        return filtered

    def _fetch_article(
        self, url: str, source: SourceConfig, verbose: bool = False
    ) -> dict[str, Any] | tuple[None, str]:
        """Fetch and extract article content.

        Args:
            url: Article URL to fetch
            source: Source configuration
            verbose: If True, print detailed progress

        Returns:
            Dictionary with article data, or tuple of (None, filter_reason) if filtered out

        Raises:
            requests.RequestException: If HTTP request fails
            ValueError: If content extraction fails
        """
        # Security validation
        validate_url_for_ssrf(url)

        # Fetch HTML
        response = self.session.get(url, timeout=self.config.timeout_seconds)
        response.raise_for_status()

        # Extract content with trafilatura
        html = response.text
        markdown = trafilatura.extract(html, output_format="markdown")

        if not markdown:
            raise ValueError("Failed to extract content from page")

        # Extract metadata
        metadata = trafilatura.extract_metadata(html)

        # Build content data for filtering
        title = (metadata.title if metadata else None) or url
        word_count = len(markdown.split())

        content_data = {
            "title": title,
            "text": markdown,
            "word_count": word_count,
            "url": url,
            "created_date": metadata.date if metadata else None,
        }

        # Apply filters (combine default + source-specific)
        filters = self._merge_filters(self.config.default_filters, source.filters)

        if filters:
            # Check minimum content length first (more specific)
            if filters.min_content_length and word_count < filters.min_content_length:
                return None, f"too_short_{word_count}words"

            filter_criteria = {
                "max_age_days": filters.max_age_days,
                "include_keywords": filters.include_keywords,
                "exclude_keywords": filters.exclude_keywords,
            }

            if not apply_content_filter(content_data, filter_criteria):
                # Determine which filter failed for more specific reason
                if filters.exclude_keywords:
                    from tools._shared.filters import matches_keywords_debug

                    combined_text = f"{content_data.get('title', '')} {content_data.get('text', '')}"
                    matched, keyword = matches_keywords_debug(combined_text, filters.exclude_keywords)
                    if matched:
                        return None, f"excluded_keyword_{keyword}"

                if filters.include_keywords:
                    return None, "missing_required_keywords"

                if filters.max_age_days and content_data.get("created_date"):
                    return None, "too_old"

                return None, "filtered"

        return {
            "title": title,
            "markdown": markdown,
            "word_count": word_count,
            "created_date": metadata.date if metadata else None,
            "author": metadata.author if metadata else None,
            "description": metadata.description if metadata else None,
        }

    def _merge_filters(
        self, default: FilterCriteria | None, specific: FilterCriteria | None
    ) -> FilterCriteria | None:
        """Merge default and source-specific filters.

        Source-specific filters take precedence over defaults.

        Args:
            default: Default filter criteria
            specific: Source-specific filter criteria

        Returns:
            Merged filter criteria or None if no filters
        """
        if not default and not specific:
            return None

        if not default:
            return specific

        if not specific:
            return default

        # Merge - specific overrides default
        return FilterCriteria(
            max_age_days=specific.max_age_days if specific.max_age_days is not None else default.max_age_days,
            min_content_length=(
                specific.min_content_length
                if specific.min_content_length is not None
                else default.min_content_length
            ),
            include_keywords=specific.include_keywords or default.include_keywords,
            exclude_keywords=specific.exclude_keywords or default.exclude_keywords,
        )

    def _save_article(self, url: str, result: dict[str, Any], verbose: bool = False) -> None:
        """Save article to markdown file.

        Args:
            url: Article URL
            result: Article data from _fetch_article
            verbose: If True, print detailed progress
        """
        # Generate safe filename
        title = result["title"]
        safe_title = sanitize_filename(title)
        filename = f"{datetime.now().strftime('%Y-%m-%d')}-{safe_title}.md"

        # Build frontmatter
        collected_date = datetime.now().isoformat()
        frontmatter = {
            "title": title,
            "url": url,
            "source": "web_direct",
            "created_date": result.get("created_date"),
            "collected_date": collected_date,
            "word_count": result["word_count"],
        }

        # Add optional metadata
        if result.get("author"):
            frontmatter["author"] = result["author"]
        if result.get("description"):
            frontmatter["description"] = result["description"]

        # Write file using shared output module
        filepath = Path(self.config.output_dir) / filename
        write_markdown_file(
            output_file_path=str(filepath),
            markdown_content=result["markdown"],
            metadata_dict=frontmatter,
        )

        # Update state
        self.state[url] = {
            "collected_date": collected_date,
            "word_count": result["word_count"],
            "status": "success",
            "filename": filename,
        }
