"""Web articles discovery collector.

This module discovers article links from configured sources using Firecrawl API.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml
from firecrawl import V1FirecrawlApp
from tools._shared.storage import SqliteStateManager

from .config import WebArticlesConfig


class WebArticlesDiscoverer:
    """Discovers article links from configured web sources."""

    def __init__(self, config: WebArticlesConfig):
        """Initialize the discoverer.

        Args:
            config: Web articles configuration

        Raises:
            ValueError: If FIRECRAWL_API_KEY is not set
        """
        self.config = config
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

        if not self.firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable not found")

        self.scraper = V1FirecrawlApp(api_key=self.firecrawl_api_key)

        # Initialize state manager with SQLite backend
        state_db_path = str(Path(self.config.state_file).with_suffix(".db"))
        self.state_manager = SqliteStateManager(state_db_path)

    def discover(self, force: bool = False, verbose: bool = False) -> dict:
        """Discover links from all configured sources.

        Args:
            force: If True, re-discover all links (ignore state)
            verbose: If True, print detailed progress information

        Returns:
            Dictionary with discovery statistics and results
        """
        if verbose:
            print("\n=== Stage 1: Link Discovery ===\n")

        # Get global exclude keywords
        exclude_keywords = self.config.exclude_keywords
        exclude_keywords_lower = [kw.lower() for kw in exclude_keywords]

        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

        # Load state (tracks already-discovered URLs)
        if not force:
            # Get all previously discovered URLs from state
            discovered_items = self.state_manager.get_processed_items(source_type="web_articles")
            discovered_urls_set = {item[0] for item in discovered_items}  # item[0] is item_id (URL)

            if discovered_items:
                if verbose:
                    # Get last_run from most recent item's timestamp
                    last_run = discovered_items[0][3] if discovered_items else None  # item[3] is timestamp
                    if last_run:
                        print(f"ℹ️  Last run: {last_run}")
                    print(f"ℹ️  Previously discovered: {len(discovered_urls_set)} URLs")
                    print("ℹ️  State tracking active (use --force to bypass)\n")
        else:
            if verbose:
                print("⚠️  --force flag detected: Re-discovering all links (ignoring state)\n")
            discovered_urls_set = set()

        # Collect all sources data for combined YAML file
        all_sources_data = []
        total_new_links = 0
        total_skipped_links = 0
        total_excluded_links = 0

        for idx, source in enumerate(self.config.sources, 1):
            if verbose:
                print(f"\n[{idx}/{len(self.config.sources)}] Crawling: {source.url}")
                print(f"Max depth: {source.max_depth}")
                keywords = source.keywords
                print(f"Keywords: {', '.join(keywords) if keywords else 'none'}")

            # Extract links using Firecrawl
            if verbose:
                print(f"Extracting links from {source.url}...")

            try:
                discovered_links = self._extract_links(source.url)
            except Exception as e:
                if verbose:
                    print(f"⚠️  Error extracting links: {e}")
                    print("  → Skipping source")
                continue

            if verbose:
                print(f"Found {len(discovered_links)} total links")

            # Filter out already-discovered links
            new_links = []
            skipped_count = 0
            excluded_count = 0

            for link in discovered_links:
                # Validate link structure
                if not isinstance(link, dict) or "url" not in link:
                    continue

                # Check against global exclude keywords
                url_lower = link["url"].lower()
                title_lower = link.get("title", "").lower()

                is_excluded = False
                if exclude_keywords_lower:
                    for keyword in exclude_keywords_lower:
                        if keyword in url_lower or keyword in title_lower:
                            excluded_count += 1
                            is_excluded = True
                            break

                if is_excluded:
                    continue

                # Check if already discovered
                if link["url"] not in discovered_urls_set:
                    new_links.append(link)
                    discovered_urls_set.add(link["url"])
                else:
                    skipped_count += 1

            if verbose:
                print(
                    f"  → {len(new_links)} new links, {skipped_count} already seen, "
                    f"{excluded_count} excluded by keywords"
                )

            total_new_links += len(new_links)
            total_skipped_links += skipped_count
            total_excluded_links += excluded_count

            # Only include new links in output
            if new_links:
                source_data = {
                    "source_url": source.url,
                    "discovery_date": datetime.now().strftime("%Y-%m-%d"),
                    "notes": f"Links discovered from {source.url} ({len(new_links)} new)",
                    "links": [
                        {"url": link["url"], "title": link["title"], "matched_keywords": []} for link in new_links
                    ],
                }
                all_sources_data.append(source_data)

        # Update state - mark each new URL as discovered
        for url in discovered_urls_set:
            if not self.state_manager.is_item_processed(url):
                # Extract source name from URL for better querying
                parsed_url = urlparse(url)
                source_name = parsed_url.netloc or "unknown"
                self.state_manager.mark_item_processed(
                    item_id=url, source_type="web_articles", source_name=source_name
                )

        # Write combined YAML file with new links only
        if total_new_links > 0:
            self._write_review_file(all_sources_data, total_new_links)

            if verbose:
                print("\n=== Discovery Complete ===")
                print(f"✅ Review file created: {self.config.review_file}")
                print(f"📊 Processed {len(self.config.sources)} source(s)")
                print(f"🆕 New links: {total_new_links}")
                print(f"⏭️  Skipped (already seen): {total_skipped_links}")
                print(f"🚫 Excluded (by keywords): {total_excluded_links}")
                print(f"💾 Total in state: {len(discovered_urls_set)}")
                print("\n📝 Next steps:")
                print(f"1. Review and edit {self.config.review_file}")
                print("2. Delete or comment out unwanted links")
                print("3. Run: web-fetch\n")
        else:
            if verbose:
                print("\n=== Discovery Complete ===")
                print("ℹ️  No new links found")
                print(f"📊 Processed {len(self.config.sources)} source(s)")
                print(f"⏭️  All {total_skipped_links} links already discovered")
                print(f"🚫 Excluded (by keywords): {total_excluded_links}")
                print(f"💾 Total in state: {len(discovered_urls_set)}")
                print("\n💡 Tip: Use --force to re-discover all links\n")

        return {
            "sources_processed": len(self.config.sources),
            "new_links": total_new_links,
            "skipped_links": total_skipped_links,
            "excluded_links": total_excluded_links,
            "total_discovered": len(discovered_urls_set),
        }

    def _extract_links(self, url: str) -> list[dict]:
        """Extract links from a webpage using Firecrawl.

        Uses the map_url() endpoint for efficient link discovery, with fallback to scrape_url().

        Args:
            url: The webpage URL to extract links from

        Returns:
            List of discovered links with url and title
        """
        extracted_links = []
        markdown_content = ""

        # Primary method: Use map_url() for fast link discovery
        try:
            map_result = self.scraper.map_url(url=url)

            # Extract URLs from map response
            # map_url returns various formats, handle them all
            if hasattr(map_result, "links"):
                links_on_page = map_result.links or []
            elif isinstance(map_result, dict):
                # Check for 'links' or 'urls' key in response
                links_on_page = map_result.get("links", map_result.get("urls", []))
            elif isinstance(map_result, list):
                # Direct list of URLs
                links_on_page = map_result
            else:
                links_on_page = []

            # Convert to list if needed
            if links_on_page and isinstance(links_on_page, list):
                for link_url in links_on_page:
                    if isinstance(link_url, str):
                        # Extract title from URL since map doesn't provide titles
                        title = self._extract_title_from_url(link_url)
                        extracted_links.append({"url": link_url, "title": title})
                    elif isinstance(link_url, dict):
                        # Some responses might include title
                        url_str = link_url.get("url", link_url.get("link", ""))
                        if url_str:
                            title = link_url.get("title", self._extract_title_from_url(url_str))
                            extracted_links.append({"url": url_str, "title": title})

        except Exception:
            # If map_url fails, fall through to scrape_url fallback
            pass

        # Fallback method: Use scrape_url if map_url didn't return results
        if not extracted_links:
            try:
                result = self.scraper.scrape_url(url=url, formats=["markdown", "links"])

                # Extract content from V1 API response
                if hasattr(result, "markdown"):
                    markdown_content = result.markdown or ""
                elif isinstance(result, dict):
                    markdown_value = result.get("markdown", result.get("content", ""))
                    markdown_content = markdown_value if isinstance(markdown_value, str) else ""

                if hasattr(result, "links"):
                    links_on_page = result.links or []
                elif isinstance(result, dict):
                    links_value = result.get("linksOnPage", result.get("links", []))
                    links_on_page = links_value if isinstance(links_value, list) else []
                else:
                    links_on_page = []

                # Process links from scrape_url
                if links_on_page:
                    for link_url in links_on_page:
                        if isinstance(link_url, str):
                            # Try to find a title in the markdown for this link
                            title = self._find_title_in_markdown(link_url, markdown_content)
                            if not title:
                                title = self._extract_title_from_url(link_url)

                            extracted_links.append({"url": link_url, "title": title})

                # Last resort: Extract from markdown content
                if not extracted_links and markdown_content:
                    extracted_links = self._extract_links_from_markdown(markdown_content, url)

            except Exception:
                # If both methods fail, return empty list
                pass

        # Remove duplicates
        seen_urls = set()
        unique_links = []
        for link in extracted_links:
            if link["url"] not in seen_urls:
                seen_urls.add(link["url"])
                unique_links.append(link)

        # Filter to only article-like links
        filtered_links = self._filter_article_links(unique_links, url)

        return filtered_links

    def _find_title_in_markdown(self, url: str, markdown: str) -> str | None:
        """Find the title for a URL in the markdown content.

        Args:
            url: URL to find title for
            markdown: Markdown content to search

        Returns:
            Title if found, None otherwise
        """
        # Escape special regex characters in URL
        escaped_url = re.escape(url)

        # Pattern to find [Title](url) format
        pattern = rf"\[([^\]]+)\]\({escaped_url}\)"

        match = re.search(pattern, markdown)
        if match:
            return match.group(1).strip()

        # Also try without protocol
        url_without_protocol = url.replace("https://", "").replace("http://", "")
        pattern2 = rf"\[([^\]]+)\]\([^\)]*{re.escape(url_without_protocol)}[^\)]*\)"

        match2 = re.search(pattern2, markdown)
        if match2:
            return match2.group(1).strip()

        return None

    def _extract_links_from_markdown(self, markdown: str, base_url: str) -> list[dict]:
        """Extract links from markdown content.

        Args:
            markdown: Markdown content
            base_url: Base URL for resolving relative links

        Returns:
            List of extracted links
        """
        links = []

        # Pattern to match markdown links: [text](url)
        pattern = r"\[([^\]]+)\]\(([^\)]+)\)"

        for match in re.finditer(pattern, markdown):
            title = match.group(1).strip()
            link_url = match.group(2).strip()

            # Skip anchors and javascript
            if link_url.startswith("#") or link_url.startswith("javascript:"):
                continue

            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, link_url)

            links.append({"url": absolute_url, "title": title})

        return links

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a readable title from a URL path.

        Args:
            url: URL to extract title from

        Returns:
            Extracted title
        """
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            return parsed.netloc

        # Get the last part of the path
        parts = path.split("/")
        last_part = parts[-1]

        # Remove file extension
        title = re.sub(r"\.[a-z]+$", "", last_part)

        # Replace hyphens and underscores with spaces
        title = title.replace("-", " ").replace("_", " ")

        # Capitalize words
        title = " ".join(word.capitalize() for word in title.split())

        return title if title else url

    def _filter_article_links(self, links: list[dict], base_url: str) -> list[dict]:
        """Filter links to only include article/news/blog content.

        Args:
            links: List of links to filter
            base_url: Base URL to filter against

        Returns:
            Filtered list of article-like links
        """
        filtered = []
        base_domain = urlparse(base_url).netloc

        for link in links:
            url = link["url"]
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
                filtered.append(link)

        return filtered

    def _write_review_file(self, sources_data: list[dict], total_links: int) -> None:
        """Write the review file for discovered links.

        Args:
            sources_data: List of source data dictionaries
            total_links: Total number of new links
        """
        combined_data = {
            "file_metadata": {
                "generated_by": "Link Review File Generator",
                "generated_on": datetime.now().strftime("%Y-%m-%d"),
                "total_sources": len(sources_data),
                "total_links": total_links,
            },
            "sources": sources_data,
        }

        # Create header with instructions
        yaml_header = f"""# {self.config.review_file}
# Purpose: This file contains NEW links discovered for human review before content fetching.
# Instructions:
#  - Review each source and its links below.
#  - Delete unwanted link entries or comment them out (prefix the entire link block with "#").
#  - Verify each URL and title are correct.
#  - When ready to fetch content, run: web-fetch
#
# How to edit:
#  - To remove a link permanently: delete the entire "- url: ..." block for that link.
#  - To disable a link without deleting: add a "#" at the start of each line of that link block.
#  - Keep the YAML structure valid after edits.
#
# Note: matched_keywords lists may be empty when no keywords were matched during filtering.
#
"""

        # Ensure parent directory exists
        Path(self.config.review_file).parent.mkdir(parents=True, exist_ok=True)

        with open(self.config.review_file, "w") as f:
            f.write(yaml_header)
            yaml.dump(combined_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
