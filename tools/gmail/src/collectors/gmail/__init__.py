"""Gmail collector for Signal system.

This package provides Gmail content collection functionality using the Gmail API.
"""

from .collector import GmailCollector
from .config import GmailCollectorConfig, load_gmail_config

__all__ = ["GmailCollector", "GmailCollectorConfig", "load_gmail_config"]
