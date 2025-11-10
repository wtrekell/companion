"""Reddit content collector using PRAW library.

This module provides the main Reddit collection functionality with state tracking and content filtering.
"""

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import praw
from praw.models import Comment, Submission

from tools._shared.config import get_env_var
from tools._shared.exceptions import StateManagementError
from tools._shared.filters import apply_content_filter
from tools._shared.output import ensure_folder_structure, update_existing_file, write_markdown_file
from tools._shared.security import sanitize_filename
from tools._shared.storage import JsonStateManager

from .config import RedditCollectorConfig, SubredditConfig

logger = logging.getLogger(__name__)


class RedditCollector:
    """Reddit content collector with state tracking and filtering."""

    def __init__(self, config: RedditCollectorConfig):
        """
        Initialize Reddit collector with configuration.

        Args:
            config: Reddit collector configuration

        Raises:
            ValueError: If Reddit credentials are missing
            praw.exceptions.PRAWException: If Reddit API connection fails
        """
        self.config = config
        self.state_file = Path(config.output_dir) / "reddit_state.json"
        self.state_manager = JsonStateManager(str(self.state_file))
        self.state: dict[str, dict[str, Any]] = self.state_manager.load_state()

        # Initialize Reddit API client
        try:
            self.reddit = praw.Reddit(
                client_id=config.client_id or get_env_var("REDDIT_CLIENT_ID"),
                client_secret=config.client_secret or get_env_var("REDDIT_CLIENT_SECRET"),
                user_agent=config.user_agent,
            )
            # Test connection with read-only endpoint that doesn't require user auth
            try:
                _ = self.reddit.subreddit("test").display_name
            except AttributeError:
                # Fallback if test subreddit is not accessible
                pass
        except Exception:
            # Don't expose credentials or error details in logs or exceptions
            # Authentication errors should not leak any sensitive information
            logger.error("Reddit API initialization failed - check credentials")
            raise ValueError(
                "Failed to initialize Reddit API connection. "
                "Check your REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET credentials."
            ) from None

    def _should_update_post(self, post_id: str, comment_count: int) -> bool:
        """
        Check if post should be updated based on comment count changes.

        Args:
            post_id: Reddit post ID
            comment_count: Current comment count

        Returns:
            True if post should be updated, False otherwise
        """
        if post_id not in self.state:
            return True

        stored_comment_count: int = self.state[post_id].get("comment_count", 0)
        return comment_count > stored_comment_count

    def _create_post_filename(self, submission: Submission, subreddit_name: str) -> str:
        """
        Create standardized filename for Reddit post.

        Args:
            submission: Reddit submission object
            subreddit_name: Name of the subreddit

        Returns:
            Standardized filename for the post
        """
        # Convert timestamp to date
        created_date = datetime.fromtimestamp(submission.created_utc, tz=UTC)
        date_string = created_date.strftime("%Y-%m-%d")

        # Clean title for filename using security utilities
        truncated_title = submission.title[:50] if len(submission.title) > 50 else submission.title
        clean_title = sanitize_filename(truncated_title.replace(" ", "_"))

        return f"{date_string}_r_{subreddit_name}_{clean_title}_{submission.id}.md"

    def _extract_comments(self, submission: Submission) -> str:
        """
        Extract and format comments from Reddit submission.

        Args:
            submission: Reddit submission object

        Returns:
            Formatted comments as markdown text
        """
        if not hasattr(submission, "comments") or len(submission.comments) == 0:
            return ""

        comments_markdown = "\n\n## Comments\n\n"

        # Expand ALL comments to get full thread
        submission.comments.replace_more(limit=None)

        for comment in submission.comments:
            if isinstance(comment, Comment) and comment.body != "[deleted]":
                # Add null check for deleted user accounts
                author_name = str(comment.author) if comment.author else "[deleted]"
                comment_time = datetime.fromtimestamp(comment.created_utc, tz=UTC)
                comments_markdown += (
                    f"### Comment by u/{author_name} ({comment_time.strftime('%Y-%m-%d %H:%M UTC')})\n\n"
                )
                comments_markdown += f"Score: {comment.score}\n\n"
                comments_markdown += f"{comment.body}\n\n---\n\n"

        return comments_markdown

    def _save_post(self, submission: Submission, subreddit_config: SubredditConfig) -> str:
        """
        Save Reddit post as markdown file.

        Args:
            submission: Reddit submission object
            subreddit_config: Subreddit configuration

        Returns:
            Path to the saved file

        Raises:
            OSError: If file writing fails
        """
        # Create output directory structure
        output_dir = ensure_folder_structure(self.config.output_dir, "reddit", subreddit_config.name)

        # Generate filename
        filename = self._create_post_filename(submission, subreddit_config.name)
        file_path = output_dir / filename

        # Prepare metadata
        created_date = datetime.fromtimestamp(submission.created_utc, tz=UTC)
        metadata = {
            "title": submission.title,
            "author": str(submission.author) if submission.author else "[deleted]",
            "score": submission.score,
            "created_date": created_date,
            "subreddit": subreddit_config.name,
            "url": f"https://reddit.com{submission.permalink}",
            "post_id": submission.id,
            "comment_count": submission.num_comments,
            "upvote_ratio": getattr(submission, "upvote_ratio", None),
            "flair": submission.link_flair_text,
            "collected_date": datetime.now(tz=UTC),
        }

        # Prepare content
        content_parts = [f"# {submission.title}\n"]

        if submission.selftext:
            content_parts.append(f"\n{submission.selftext}\n")
        elif submission.url and submission.url != f"https://reddit.com{submission.permalink}":
            content_parts.append(f"\n**Link:** {submission.url}\n")

        # Add comments if requested
        if subreddit_config.include_comments:
            comments_content = self._extract_comments(submission)
            if comments_content:
                content_parts.append(comments_content)

        markdown_content = "\n".join(content_parts)

        # Write file (only if content changed)
        full_content_with_metadata = ""
        if metadata:
            frontmatter_lines = ["---"]
            for key, value in metadata.items():
                if value is not None:
                    if isinstance(value, str):
                        frontmatter_lines.append(f'{key}: "{value}"')
                    else:
                        frontmatter_lines.append(f"{key}: {value}")
            frontmatter_lines.append("---")
            full_content_with_metadata = "\n".join(frontmatter_lines) + "\n\n" + markdown_content
        else:
            full_content_with_metadata = markdown_content

        # Check if file needs updating
        if update_existing_file(str(file_path), full_content_with_metadata):
            write_markdown_file(str(file_path), markdown_content, metadata)
            print(f"Saved: {filename}")
        else:
            print(f"No changes: {filename}")

        return str(file_path)

    def collect_subreddit(self, subreddit_config: SubredditConfig) -> dict[str, Any]:
        """
        Collect posts from a specific subreddit.

        Args:
            subreddit_config: Configuration for the subreddit

        Returns:
            Collection statistics

        Raises:
            praw.exceptions.PRAWException: If Reddit API errors occur
        """
        print(f"Collecting from r/{subreddit_config.name}...")

        stats: dict[str, Any] = {
            "subreddit": subreddit_config.name,
            "posts_processed": 0,
            "posts_saved": 0,
            "posts_updated": 0,
            "posts_skipped": 0,
            "errors": 0,
        }

        try:
            subreddit = self.reddit.subreddit(subreddit_config.name)

            # Determine time filter for 'top' sort when age limit exists
            filters_to_use = subreddit_config.filters or self.config.default_filters

            # Get posts based on sort method
            if subreddit_config.sort_by == "hot":
                posts = subreddit.hot(limit=subreddit_config.max_posts)
            elif subreddit_config.sort_by == "new":
                posts = subreddit.new(limit=subreddit_config.max_posts)
            elif subreddit_config.sort_by == "top":
                # Apply time filter for 'top' sort when max_age_days is specified
                if filters_to_use and filters_to_use.max_age_days and filters_to_use.max_age_days <= 7:
                    posts = subreddit.top(limit=subreddit_config.max_posts, time_filter="week")
                elif filters_to_use and filters_to_use.max_age_days and filters_to_use.max_age_days <= 30:
                    posts = subreddit.top(limit=subreddit_config.max_posts, time_filter="month")
                else:
                    posts = subreddit.top(limit=subreddit_config.max_posts)
            elif subreddit_config.sort_by == "rising":
                posts = subreddit.rising(limit=subreddit_config.max_posts)
            else:
                posts = subreddit.hot(limit=subreddit_config.max_posts)

            for submission in posts:
                stats["posts_processed"] = stats["posts_processed"] + 1

                try:
                    # Check if post needs updating BEFORE applying filters and fetching comments
                    if not self._should_update_post(submission.id, submission.num_comments):
                        stats["posts_skipped"] = stats["posts_skipped"] + 1
                        continue

                    # Apply filters (filters_to_use already determined above)

                    content_data = {
                        "title": submission.title,
                        "text": submission.selftext or "",
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "created_date": datetime.fromtimestamp(submission.created_utc, tz=UTC),
                    }

                    filter_criteria = {
                        "max_age_days": filters_to_use.max_age_days,
                        "min_score": filters_to_use.min_score,
                        "min_comments": filters_to_use.min_comments,
                        "include_keywords": filters_to_use.include_keywords,
                        "exclude_keywords": filters_to_use.exclude_keywords,
                    }

                    if not apply_content_filter(content_data, filter_criteria):
                        stats["posts_skipped"] = stats["posts_skipped"] + 1
                        continue

                    # Save the post (we already checked if update is needed)
                    file_path = self._save_post(submission, subreddit_config)

                    # Check if this is an update or new post before modifying state
                    is_existing_post = submission.id in self.state and "last_updated" in self.state[submission.id]

                    # Update state atomically using state manager
                    new_state_data = {
                        submission.id: {
                            "comment_count": submission.num_comments,
                            "last_updated": datetime.now(tz=UTC).isoformat(),
                            "file_path": file_path,
                        }
                    }

                    try:
                        self.state_manager.update_state(new_state_data)
                        # Update local state after successful atomic update
                        self.state.update(new_state_data)
                    except StateManagementError as state_error:
                        print(f"Warning: Failed to update state for post {submission.id}: {state_error}")

                    if is_existing_post:
                        stats["posts_updated"] = stats["posts_updated"] + 1
                    else:
                        stats["posts_saved"] = stats["posts_saved"] + 1

                    # Rate limiting
                    time.sleep(self.config.rate_limit_seconds)

                except Exception as post_error:
                    print(f"Error processing post {submission.id}: {post_error}")
                    stats["errors"] = stats["errors"] + 1
                    continue

        except Exception as subreddit_error:
            print(f"Error accessing subreddit r/{subreddit_config.name}: {subreddit_error}")
            stats["errors"] = stats["errors"] + 1

        # State is saved atomically per post, no batch save needed

        return stats

    def collect_all_subreddits(self) -> dict[str, Any]:
        """
        Collect posts from all configured subreddits.

        Returns:
            Overall collection statistics
        """
        print(f"Starting Reddit collection for {len(self.config.subreddits)} subreddits...")

        overall_stats: dict[str, Any] = {
            "total_subreddits": len(self.config.subreddits),
            "subreddits_processed": 0,
            "total_posts_processed": 0,
            "total_posts_saved": 0,
            "total_posts_updated": 0,
            "total_posts_skipped": 0,
            "total_errors": 0,
            "subreddit_stats": [],
        }

        for subreddit_config in self.config.subreddits:
            stats = self.collect_subreddit(subreddit_config)
            overall_stats["subreddit_stats"].append(stats)
            overall_stats["subreddits_processed"] = overall_stats["subreddits_processed"] + 1
            overall_stats["total_posts_processed"] = overall_stats["total_posts_processed"] + stats["posts_processed"]
            overall_stats["total_posts_saved"] = overall_stats["total_posts_saved"] + stats["posts_saved"]
            overall_stats["total_posts_updated"] = overall_stats["total_posts_updated"] + stats["posts_updated"]
            overall_stats["total_posts_skipped"] = overall_stats["total_posts_skipped"] + stats["posts_skipped"]
            overall_stats["total_errors"] = overall_stats["total_errors"] + stats["errors"]

        print(f"Reddit collection completed. Processed {overall_stats['total_posts_processed']} posts.")

        return overall_stats
