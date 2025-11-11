"""Configuration classes for Reddit collector.

This module defines typed configuration structures for Reddit collection settings.
"""

import re
from dataclasses import dataclass, field

from tools._shared.config import get_env_var, load_yaml_config


@dataclass
class FilterCriteria:
    """Content filtering criteria for Reddit posts."""

    max_age_days: int | None = None
    min_score: int | None = None
    min_comments: int | None = None
    include_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)


@dataclass
class SubredditConfig:
    """Configuration for a specific subreddit."""

    name: str
    filters: FilterCriteria | None = None
    max_posts: int = 50
    include_comments: bool = True
    sort_by: str = "hot"  # hot, new, top, rising

    def __post_init__(self) -> None:
        """Validate subreddit configuration after initialization."""
        # Validate subreddit name format
        if not self._is_valid_subreddit_name(self.name):
            raise ValueError(f"Invalid subreddit name format: {self.name}")

        # Validate sort parameter
        valid_sorts = {"hot", "new", "top", "rising"}
        if self.sort_by not in valid_sorts:
            raise ValueError(f"Invalid sort parameter '{self.sort_by}'. Must be one of: {valid_sorts}")

        # Validate max_posts bounds
        if not (1 <= self.max_posts <= 1000):
            raise ValueError(f"max_posts must be between 1 and 1000, got: {self.max_posts}")

    def _is_valid_subreddit_name(self, name: str) -> bool:
        """Validate subreddit name against Reddit naming conventions."""
        if not name or len(name) < 1 or len(name) > 21:
            return False

        # Reddit subreddit names: 3-21 chars, alphanumeric + underscore, no consecutive underscores
        pattern = re.compile(r"^[a-zA-Z0-9_]{1,21}$")
        if not pattern.match(name):
            return False

        # No consecutive underscores
        if "__" in name:
            return False

        # Cannot start or end with underscore
        if name.startswith("_") or name.endswith("_"):
            return False

        return True


@dataclass
class RedditCollectorConfig:
    """Main configuration for Reddit collector."""

    output_dir: str
    rate_limit_seconds: float = 2.0
    default_filters: FilterCriteria = field(default_factory=FilterCriteria)
    subreddits: list[SubredditConfig] = field(default_factory=list)

    # Reddit API credentials (from environment)
    client_id: str = ""
    client_secret: str = ""
    user_agent: str = "Signal:Reddit:Collector:v2.0.0"

    def __post_init__(self) -> None:
        """Validate Reddit collector configuration after initialization."""
        # Validate rate limit bounds
        if not (0.1 <= self.rate_limit_seconds <= 300.0):
            raise ValueError(f"rate_limit_seconds must be between 0.1 and 300.0, got: {self.rate_limit_seconds}")

        # Validate output directory
        if not self.output_dir or len(self.output_dir.strip()) == 0:
            raise ValueError("output_dir cannot be empty")

        # Validate user agent
        if not self.user_agent or len(self.user_agent.strip()) == 0:
            raise ValueError("user_agent cannot be empty")

        # Validate credentials if provided
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """Validate Reddit API credentials."""
        # Get credentials from environment or config
        client_id = self.client_id or get_env_var("REDDIT_CLIENT_ID", "")
        client_secret = self.client_secret or get_env_var("REDDIT_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            raise ValueError(
                "Reddit API credentials are required. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET "
                "environment variables or provide in config."
            )

        # Validate credential format (Reddit client IDs are typically 14 chars, secrets are 27 chars)
        if len(client_id) < 10 or len(client_id) > 30:
            raise ValueError("Invalid Reddit client_id format")

        if len(client_secret) < 20 or len(client_secret) > 50:
            raise ValueError("Invalid Reddit client_secret format")


def load_reddit_config(config_path: str) -> RedditCollectorConfig:
    """
    Load Reddit collector configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Parsed configuration object

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If configuration is invalid
    """
    raw_config = load_yaml_config(config_path)

    # Parse and validate default filters
    default_filters_data = raw_config.get("default_filters", {})
    if not isinstance(default_filters_data, dict):
        raise ValueError("default_filters must be a dictionary")

    # Validate filter fields if present
    if "max_age_days" in default_filters_data:
        max_age = default_filters_data["max_age_days"]
        if not isinstance(max_age, int) or max_age < 1:
            raise ValueError("max_age_days must be a positive integer")

    if "min_score" in default_filters_data:
        min_score = default_filters_data["min_score"]
        if not isinstance(min_score, int):
            raise ValueError("min_score must be an integer")

    if "min_comments" in default_filters_data:
        min_comments = default_filters_data["min_comments"]
        if not isinstance(min_comments, int):
            raise ValueError("min_comments must be an integer")

    for keyword_field in ["include_keywords", "exclude_keywords"]:
        if keyword_field in default_filters_data:
            keywords = default_filters_data[keyword_field]
            if not isinstance(keywords, list):
                raise ValueError(f"{keyword_field} must be a list")
            if not all(isinstance(kw, str) for kw in keywords):
                raise ValueError(f"All items in {keyword_field} must be strings")

    default_filters = FilterCriteria(
        max_age_days=default_filters_data.get("max_age_days"),
        min_score=default_filters_data.get("min_score"),
        min_comments=default_filters_data.get("min_comments"),
        include_keywords=default_filters_data.get("include_keywords", []),
        exclude_keywords=default_filters_data.get("exclude_keywords", []),
    )

    # Parse subreddit configurations
    subreddits: list[SubredditConfig] = []
    subreddit_list = raw_config.get("subreddits", [])

    if not subreddit_list:
        raise ValueError("At least one subreddit must be configured")

    if not isinstance(subreddit_list, list):
        raise ValueError("subreddits must be a list")

    for subreddit_data in subreddit_list:
        # Validate required fields first
        if "name" not in subreddit_data:
            raise ValueError(f"Subreddit at index {len(subreddits)} is missing required 'name' field")

        subreddit_name = subreddit_data["name"]
        if not isinstance(subreddit_name, str):
            raise ValueError(f"Subreddit name must be a string, got: {type(subreddit_name).__name__}")

        # Parse and validate subreddit-specific filters if present
        subreddit_filters = None
        if "filters" in subreddit_data:
            filter_data = subreddit_data["filters"]
            if not isinstance(filter_data, dict):
                raise ValueError(f"filters for subreddit '{subreddit_name}' must be a dictionary")

            # Validate filter fields similar to default filters
            if "max_age_days" in filter_data:
                max_age = filter_data["max_age_days"]
                if not isinstance(max_age, int) or max_age < 1:
                    raise ValueError(f"max_age_days for subreddit '{subreddit_name}' must be a positive integer")

            if "min_score" in filter_data:
                min_score = filter_data["min_score"]
                if not isinstance(min_score, int):
                    raise ValueError(f"min_score for subreddit '{subreddit_name}' must be an integer")

            if "min_comments" in filter_data:
                min_comments = filter_data["min_comments"]
                if not isinstance(min_comments, int):
                    raise ValueError(f"min_comments for subreddit '{subreddit_name}' must be an integer")

            for keyword_field in ["include_keywords", "exclude_keywords"]:
                if keyword_field in filter_data:
                    keywords = filter_data[keyword_field]
                    if not isinstance(keywords, list):
                        raise ValueError(f"{keyword_field} for subreddit '{subreddit_name}' must be a list")
                    if not all(isinstance(kw, str) for kw in keywords):
                        raise ValueError(
                            f"All items in {keyword_field} for subreddit '{subreddit_name}' must be strings"
                        )

            subreddit_filters = FilterCriteria(
                max_age_days=filter_data.get("max_age_days"),
                min_score=filter_data.get("min_score"),
                min_comments=filter_data.get("min_comments"),
                include_keywords=filter_data.get("include_keywords", []),
                exclude_keywords=filter_data.get("exclude_keywords", []),
            )

        # Validate additional subreddit fields
        max_posts = subreddit_data.get("max_posts", 50)
        if not isinstance(max_posts, int) or max_posts < 1 or max_posts > 1000:
            raise ValueError(f"max_posts for subreddit '{subreddit_name}' must be between 1 and 1000, got: {max_posts}")

        sort_by = subreddit_data.get("sort_by", "hot")
        if not isinstance(sort_by, str):
            raise ValueError(
                f"sort_by must be a string for subreddit '{subreddit_name}', got: {type(sort_by).__name__}"
            )

        include_comments = subreddit_data.get("include_comments", True)
        if not isinstance(include_comments, bool):
            raise ValueError(f"include_comments for subreddit '{subreddit_name}' must be a boolean")

        # Create subreddit config with validation (SubredditConfig.__post_init__ will validate)
        try:
            subreddit_config = SubredditConfig(
                name=subreddit_name,
                filters=subreddit_filters,
                max_posts=max_posts,
                include_comments=include_comments,
                sort_by=sort_by,
            )
        except ValueError as validation_error:
            raise ValueError(
                f"Invalid configuration for subreddit '{subreddit_name}': {validation_error}"
            ) from validation_error
        subreddits.append(subreddit_config)

    # Build main configuration
    # Validate required main config fields
    if "output_dir" not in raw_config:
        raise ValueError("Missing required 'output_dir' field in Reddit configuration")

    # Validate output_dir is a string
    if not isinstance(raw_config["output_dir"], str):
        raise ValueError("output_dir must be a string")

    # Validate rate_limit_seconds if provided
    rate_limit = raw_config.get("rate_limit_seconds", 2.0)
    if not isinstance(rate_limit, (int, float)):
        raise ValueError("rate_limit_seconds must be a number")

    # Validate user_agent if provided
    user_agent = raw_config.get("user_agent", "")
    if user_agent and not isinstance(user_agent, str):
        raise ValueError("user_agent must be a string")

    # Create main config with validation (RedditCollectorConfig.__post_init__ will validate)
    try:
        config = RedditCollectorConfig(
            output_dir=raw_config["output_dir"],
            rate_limit_seconds=rate_limit,
            default_filters=default_filters,
            subreddits=subreddits,
            client_id=raw_config.get("client_id", ""),
            client_secret=raw_config.get("client_secret", ""),
            user_agent=raw_config.get("user_agent", "Signal:Reddit:Collector:v2.0.0"),
        )
    except ValueError as validation_error:
        raise ValueError(f"Invalid Reddit collector configuration: {validation_error}") from validation_error

    return config
