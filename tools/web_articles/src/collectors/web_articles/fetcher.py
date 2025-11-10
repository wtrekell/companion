"""Web articles content fetcher.

This module fetches full article content from approved links using Firecrawl API.
"""

import os
import re
import time
from datetime import datetime
from pathlib import Path

import yaml
from firecrawl import V1FirecrawlApp

from .config import WebArticlesConfig


class WebArticlesFetcher:
    """Fetches article content from approved links."""

    def __init__(self, config: WebArticlesConfig):
        """Initialize the fetcher.

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

    def fetch(self, verbose: bool = False) -> dict:
        """Fetch content from review file.

        Args:
            verbose: If True, print detailed progress information

        Returns:
            Dictionary with fetch statistics

        Raises:
            FileNotFoundError: If review file doesn't exist
            ValueError: If review file is invalid
        """
        if verbose:
            print("\n=== Stage 2: Content Fetching ===\n")

        # Check if review file exists
        review_file = self.config.review_file
        if not os.path.exists(review_file):
            raise FileNotFoundError(f"Review file not found: {review_file}\nPlease run 'web-discover' first.")

        # Load review file
        with open(review_file) as f:
            review_data = yaml.safe_load(f)

        if not review_data or "sources" not in review_data:
            raise ValueError("Invalid review file format: missing 'sources' key")

        # Setup
        output_dir = self.config.output_dir
        rate_limit = self.config.rate_limit_seconds
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Collect all links from all sources
        all_links = []
        for source in review_data["sources"]:
            source_url = source.get("source_url", "unknown")
            links = source.get("links", [])
            for link in links:
                if isinstance(link, dict) and "url" in link:
                    all_links.append(
                        {
                            "url": link["url"],
                            "title": link.get("title", "Untitled"),
                            "source": source_url,
                        }
                    )

        if verbose:
            print(f"Review file: {review_file}")
            print(f"Output directory: {output_dir}")
            print(f"Rate limit: {rate_limit}s between requests")
            print(f"Total links to fetch: {len(all_links)}\n")

        # Fetch each article
        successful = 0
        failed = 0
        skipped = 0
        total_word_count = 0

        for idx, link in enumerate(all_links, 1):
            url = link["url"]
            title = link["title"]

            if verbose:
                print(f"[{idx}/{len(all_links)}] Fetching: {title}")
                print(f"  URL: {url}")

            # Retry logic for rate limits
            max_retries = 3
            retry_count = 0

            while retry_count <= max_retries:
                try:
                    # Call Firecrawl V1 API directly
                    result = self.scraper.scrape_url(url=url, formats=["markdown"])

                    # Extract markdown content from V1 API response
                    markdown: str = ""
                    if hasattr(result, "markdown"):
                        markdown = result.markdown or ""
                    elif isinstance(result, dict):
                        markdown_value = result.get("markdown", result.get("content", ""))
                        markdown = markdown_value if isinstance(markdown_value, str) else ""

                    if not markdown or len(markdown.strip()) < 100:
                        if verbose:
                            print(f"  ⚠️  Content too short ({len(markdown)} chars), skipping")
                        skipped += 1
                        break  # Break retry loop, move to next link

                    # Extract metadata from V1 API response
                    metadata = {}
                    if hasattr(result, "metadata"):
                        metadata = result.metadata or {}
                    elif isinstance(result, dict):
                        metadata = result.get("metadata", {})

                    # Helper function to safely get metadata values
                    def get_metadata(key: str, default: str | None = None) -> str | None:
                        if isinstance(metadata, dict):
                            value = metadata.get(key, default)
                            return value if value else default
                        return default

                    # Create filename from title
                    safe_title = re.sub(r"[^\w\s-]", "", title.lower())
                    safe_title = re.sub(r"[-\s]+", "-", safe_title)
                    safe_title = safe_title[:100]  # Limit length
                    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{safe_title}.md"
                    filepath = os.path.join(output_dir, filename)

                    # Create frontmatter with enhanced metadata
                    word_count = len(markdown.split())
                    total_word_count += word_count

                    # Build frontmatter with all available metadata
                    frontmatter_parts = [
                        "---",
                        f'title: "{title}"',
                        f'url: "{url}"',
                        f'source: "{link["source"]}"',
                    ]

                    # Add optional metadata fields
                    description = get_metadata("description")
                    if description:
                        # Escape quotes in description
                        description = description.replace('"', '\\"')
                        frontmatter_parts.append(f'description: "{description}"')
                    else:
                        frontmatter_parts.append("description: null")

                    keywords = get_metadata("keywords")
                    if keywords:
                        keywords = keywords.replace('"', '\\"')
                        frontmatter_parts.append(f'keywords: "{keywords}"')
                    else:
                        frontmatter_parts.append("keywords: null")

                    author = get_metadata("author")
                    if author:
                        author = author.replace('"', '\\"')
                        frontmatter_parts.append(f'author: "{author}"')
                    else:
                        frontmatter_parts.append("author: null")

                    # Published date (might be called publishedTime, published, or date)
                    published_date = (
                        get_metadata("publishedTime") or get_metadata("published") or get_metadata("date")
                    )
                    if published_date:
                        frontmatter_parts.append(f'published_date: "{published_date}"')
                    else:
                        frontmatter_parts.append("published_date: null")

                    frontmatter_parts.append("created_date: null")
                    frontmatter_parts.append(f'collected_date: "{datetime.now().isoformat()}"')
                    frontmatter_parts.append(f"word_count: {word_count}")

                    # Add Open Graph metadata
                    og_title = get_metadata("ogTitle")
                    if og_title:
                        og_title = og_title.replace('"', '\\"')
                        frontmatter_parts.append(f'og_title: "{og_title}"')

                    og_description = get_metadata("ogDescription")
                    if og_description:
                        og_description = og_description.replace('"', '\\"')
                        frontmatter_parts.append(f'og_description: "{og_description}"')

                    og_image = get_metadata("ogImage")
                    if og_image:
                        frontmatter_parts.append(f'og_image: "{og_image}"')

                    og_type = get_metadata("ogType")
                    if og_type:
                        frontmatter_parts.append(f'og_type: "{og_type}"')

                    og_site_name = get_metadata("ogSiteName")
                    if og_site_name:
                        og_site_name = og_site_name.replace('"', '\\"')
                        frontmatter_parts.append(f'og_site_name: "{og_site_name}"')

                    # Add Twitter metadata
                    twitter_card = get_metadata("twitterCard")
                    if twitter_card:
                        frontmatter_parts.append(f'twitter_card: "{twitter_card}"')

                    twitter_title = get_metadata("twitterTitle")
                    if twitter_title:
                        twitter_title = twitter_title.replace('"', '\\"')
                        frontmatter_parts.append(f'twitter_title: "{twitter_title}"')

                    twitter_description = get_metadata("twitterDescription")
                    if twitter_description:
                        twitter_description = twitter_description.replace('"', '\\"')
                        frontmatter_parts.append(f'twitter_description: "{twitter_description}"')

                    twitter_image = get_metadata("twitterImage")
                    if twitter_image:
                        frontmatter_parts.append(f'twitter_image: "{twitter_image}"')

                    # Add other useful metadata
                    language = get_metadata("language")
                    if language:
                        frontmatter_parts.append(f'language: "{language}"')

                    favicon = get_metadata("favicon")
                    if favicon:
                        frontmatter_parts.append(f'favicon: "{favicon}"')

                    frontmatter_parts.append("---")
                    frontmatter_parts.append("")  # Empty line after frontmatter

                    frontmatter = "\n".join(frontmatter_parts) + "\n"

                    # Write markdown file
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(frontmatter)
                        f.write(markdown)

                    if verbose:
                        print(f"  ✅ Saved ({word_count} words)")
                    successful += 1
                    break  # Success, break retry loop

                except Exception as e:
                    error_msg = str(e)

                    # Check for rate limit error (429)
                    if "429" in error_msg or "Rate limit exceeded" in error_msg:
                        retry_count += 1

                        if retry_count <= max_retries:
                            # Extract wait time from error message
                            wait_time = rate_limit * 2  # Default fallback
                            if "retry after" in error_msg.lower():
                                try:
                                    # Try to extract the suggested wait time
                                    match = re.search(r"retry after (\d+)s", error_msg)
                                    if match:
                                        wait_time = int(match.group(1)) + 2  # Add buffer
                                except Exception:
                                    pass

                            if verbose:
                                print(
                                    f"  ⚠️  Rate limit hit, waiting {wait_time}s before "
                                    f"retry {retry_count}/{max_retries}..."
                                )
                            time.sleep(wait_time)
                            continue  # Retry this link
                        else:
                            if verbose:
                                print("  ❌ Rate limit - max retries exceeded")
                            failed += 1
                            break

                    else:
                        # Non-rate-limit error
                        if verbose:
                            print(f"  ❌ Error: {e}")
                        failed += 1
                        break  # Don't retry, move to next link

            # Rate limiting between successful requests
            if idx < len(all_links):  # Don't sleep after last item
                time.sleep(rate_limit)

        # Print summary
        if verbose:
            print("\n=== Content Fetching Complete ===")
            print(f"✅ Successfully fetched: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"⏭️  Skipped (too short): {skipped}")
            print(f"📊 Total processed: {len(all_links)}")
            if successful > 0:
                avg_words = total_word_count // successful
                print(f"📝 Average word count: {avg_words}")
            print(f"📁 Articles saved to: {output_dir}\n")

        return {
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "total": len(all_links),
            "avg_word_count": total_word_count // successful if successful > 0 else 0,
        }
