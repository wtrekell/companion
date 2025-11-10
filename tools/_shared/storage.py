"""Storage utilities for content collectors.

Simplified for personal use - no file locking or race condition handling needed.
Single user, single process execution.
"""

import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .exceptions import StateManagementError


class SqliteStateManager:
    """SQLite-based state manager for tracking processed content."""

    def __init__(self, database_file_path: str):
        """
        Initialize SQLite state manager.

        Args:
            database_file_path: Path to the SQLite database file

        Raises:
            StateManagementError: If database initialization fails
        """
        self.database_file_path = Path(database_file_path)
        self.database_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._initialize_database()
        except sqlite3.Error as e:
            raise StateManagementError(f"Failed to initialize database: {e}") from e

    def _initialize_database(self) -> None:
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.database_file_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_items (
                    item_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    processed_timestamp TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_type ON processed_items(source_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_name ON processed_items(source_name)")

    def is_item_processed(self, item_id: str) -> bool:
        """Check if an item has already been processed."""
        try:
            with sqlite3.connect(self.database_file_path) as conn:
                cursor = conn.execute("SELECT 1 FROM processed_items WHERE item_id = ?", (item_id,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            raise StateManagementError(f"Failed to check if item {item_id} is processed: {e}") from e

    def mark_item_processed(
        self, item_id: str, source_type: str, source_name: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Mark an item as processed."""
        try:
            timestamp = datetime.now().isoformat()
            metadata_json = json.dumps(metadata) if metadata else None

            with sqlite3.connect(self.database_file_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO processed_items
                       (item_id, source_type, source_name, processed_timestamp, metadata_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (item_id, source_type, source_name, timestamp, metadata_json),
                )
                conn.commit()
        except sqlite3.Error as e:
            raise StateManagementError(f"Failed to mark item {item_id} as processed: {e}") from e

    def get_processed_items(
        self, source_type: str | None = None, source_name: str | None = None, limit: int | None = None
    ) -> list[tuple[str, str, str, str, dict[str, Any] | None]]:
        """Retrieve processed items with optional filtering."""
        try:
            conditions = []
            params = []

            if source_type:
                conditions.append("source_type = ?")
                params.append(source_type)
            if source_name:
                conditions.append("source_name = ?")
                params.append(source_name)

            query = "SELECT item_id, source_type, source_name, processed_timestamp, metadata_json FROM processed_items"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY processed_timestamp DESC"
            if limit:
                query += " LIMIT ?"
                params.append(str(limit))

            with sqlite3.connect(self.database_file_path) as conn:
                cursor = conn.execute(query, params)
                results = []
                for row in cursor.fetchall():
                    item_id, source_type, source_name, timestamp, metadata_json = row
                    metadata = json.loads(metadata_json) if metadata_json else None
                    results.append((item_id, source_type, source_name, timestamp, metadata))
                return results
        except sqlite3.Error as e:
            raise StateManagementError(f"Failed to retrieve processed items: {e}") from e

    def cleanup_old_items(self, days_to_retain: int) -> int:
        """Remove processed items older than specified days."""
        try:
            cutoff = datetime.now().timestamp() - (days_to_retain * 24 * 3600)
            cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()

            with sqlite3.connect(self.database_file_path) as conn:
                cursor = conn.execute("DELETE FROM processed_items WHERE processed_timestamp < ?", (cutoff_iso,))
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            raise StateManagementError(f"Failed to cleanup old items: {e}") from e


class JsonStateManager:
    """JSON file-based state manager for lightweight state tracking."""

    def __init__(self, state_file_path: str):
        """
        Initialize JSON state manager.

        Args:
            state_file_path: Path to the JSON state file
        """
        self.state_file_path = Path(state_file_path)
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict[str, Any]:
        """Load state from JSON file."""
        if not self.state_file_path.exists():
            return {}

        try:
            with open(self.state_file_path, encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise StateManagementError(f"Invalid state file: expected dict, got {type(data).__name__}")
                return data
        except (OSError, json.JSONDecodeError) as e:
            raise StateManagementError(f"Failed to load state from {self.state_file_path}: {e}") from e

    def save_state(self, state: dict[str, Any]) -> None:
        """Save state to JSON file using atomic write."""
        try:
            # Write to temp file then atomic rename
            temp_dir = self.state_file_path.parent
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=temp_dir, delete=False) as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
                temp_path = f.name

            os.rename(temp_path, self.state_file_path)
        except (json.JSONDecodeError, OSError) as e:
            if "temp_path" in locals():
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            raise StateManagementError(f"Failed to save state to {self.state_file_path}: {e}") from e

    def update_state(self, updates: dict[str, Any]) -> None:
        """Update existing state with new values."""
        state = self.load_state()
        state.update(updates)
        self.save_state(state)

    def batch_update_state(self, batch_updates: list[dict[str, Any]]) -> None:
        """Perform multiple state updates."""
        if not batch_updates:
            return
        state = self.load_state()
        for update in batch_updates:
            state.update(update)
        self.save_state(state)
