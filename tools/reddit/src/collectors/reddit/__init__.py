"""Reddit content collector for Signal system.

This package provides Reddit content collection functionality using PRAW,
with configurable filtering, state tracking, and markdown output.
"""

from .collector import RedditCollector
from .config import FilterCriteria, RedditCollectorConfig, SubredditConfig, load_reddit_config

__all__ = [
    "RedditCollector",
    "RedditCollectorConfig",
    "SubredditConfig",
    "FilterCriteria",
    "load_reddit_config",
]
