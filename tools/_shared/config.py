"""Configuration management utilities for content collectors.

Simplified for personal use - basic YAML loading with env var substitution.
No injection prevention needed for trusted configs.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


def get_env_var(key: str, default: str | None = None) -> str:
    """Get environment variable with optional default."""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable '{key}' not set and no default provided")
    return value


def _substitute_env_vars(config: dict[str, Any]) -> dict[str, Any]:
    """
    Replace ${VAR} or ${VAR:default} with environment variable values.

    Simple recursive substitution - no injection prevention needed.
    """

    def substitute_value(value: Any) -> Any:
        if isinstance(value, str):
            # Pattern: ${VAR_NAME} or ${VAR_NAME:default}
            pattern = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")

            def replace(match: re.Match[str]) -> str:
                var_name = match.group(1).strip()
                default_val = match.group(2) if match.group(2) is not None else None
                env_val = os.getenv(var_name, default_val)
                if env_val is None:
                    raise ValueError(f"Environment variable '{var_name}' not set and no default provided")
                return env_val

            return pattern.sub(replace, value)

        elif isinstance(value, dict):
            return {k: substitute_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [substitute_value(item) for item in value]
        else:
            return value

    result = substitute_value(config)
    if not isinstance(result, dict):
        raise ValueError("Configuration root must be a dictionary")
    return result


def load_yaml_config(config_path: str) -> dict[str, Any]:
    """
    Load YAML configuration with environment variable substitution.

    Args:
        config_path: Path to YAML config file

    Returns:
        Parsed config with env vars substituted

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML parsing fails
        ValueError: If required env vars missing
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(path, encoding="utf-8") as f:
            parsed = yaml.safe_load(f)

        if parsed is None:
            return {}

        return _substitute_env_vars(parsed)

    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}") from e
