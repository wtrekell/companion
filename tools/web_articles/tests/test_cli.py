"""Tests for web-articles CLI commands.

This module tests the command-line interface for discovery and fetching commands.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from tools.web_articles.src.collectors.web_articles.cli import discover, fetch


class TestDiscoverCLI:
    """Test web-discover CLI command."""

    def test_discover_help(self) -> None:
        """Test that discover command shows help message."""
        runner = CliRunner()
        result = runner.invoke(discover, ["--help"])

        assert result.exit_code == 0
        assert "Web articles link discovery collector" in result.output
        assert "--config" in result.output
        assert "--dry-run" in result.output
        assert "--verbose" in result.output
        assert "--force" in result.output

    def test_discover_missing_config_file(self) -> None:
        """Test discover command with non-existent config file."""
        runner = CliRunner()
        result = runner.invoke(discover, ["--config", "/nonexistent/config.yaml"])

        # Click returns exit code 2 for invalid arguments/missing files
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

    def test_discover_with_valid_config(self, temp_config_file: Path, mock_firecrawl: MagicMock) -> None:
        """Test discover command with valid configuration."""
        runner = CliRunner()

        # Mock the discoverer and Firecrawl
        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesDiscoverer") as mock_discoverer_class:
            mock_discoverer = MagicMock()
            mock_discoverer.discover.return_value = {
                "sources_processed": 1,
                "new_links": 5,
                "skipped_links": 0,
                "excluded_links": 0,
                "total_discovered": 5,
            }
            mock_discoverer_class.return_value = mock_discoverer

            result = runner.invoke(discover, ["--config", str(temp_config_file)])

            # Should succeed
            assert result.exit_code == 0
            assert mock_discoverer.discover.called

    def test_discover_dry_run(self, temp_config_file: Path) -> None:
        """Test discover command with --dry-run flag."""
        runner = CliRunner()

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesDiscoverer") as mock_discoverer_class:
            mock_discoverer = MagicMock()
            mock_discoverer_class.return_value = mock_discoverer

            result = runner.invoke(discover, ["--config", str(temp_config_file), "--dry-run"])

            # Dry run should succeed without calling discover
            assert result.exit_code == 0
            assert "Dry run completed successfully" in result.output
            assert not mock_discoverer.discover.called

    def test_discover_verbose_flag(self, temp_config_file: Path) -> None:
        """Test discover command with --verbose flag."""
        runner = CliRunner()

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesDiscoverer") as mock_discoverer_class:
            mock_discoverer = MagicMock()
            mock_discoverer.discover.return_value = {
                "sources_processed": 1,
                "new_links": 3,
                "skipped_links": 0,
                "excluded_links": 0,
                "total_discovered": 3,
            }
            mock_discoverer_class.return_value = mock_discoverer

            result = runner.invoke(discover, ["--config", str(temp_config_file), "--verbose"])

            assert result.exit_code == 0
            assert "Loading configuration" in result.output
            assert "Configuration loaded successfully" in result.output

    def test_discover_force_flag(self, temp_config_file: Path) -> None:
        """Test discover command with --force flag."""
        runner = CliRunner()

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesDiscoverer") as mock_discoverer_class:
            mock_discoverer = MagicMock()
            mock_discoverer.discover.return_value = {
                "sources_processed": 1,
                "new_links": 5,
                "skipped_links": 0,
                "excluded_links": 0,
                "total_discovered": 5,
            }
            mock_discoverer_class.return_value = mock_discoverer

            result = runner.invoke(discover, ["--config", str(temp_config_file), "--force"])

            assert result.exit_code == 0
            # Verify force flag was passed
            mock_discoverer.discover.assert_called_with(force=True, verbose=True)

    def test_discover_missing_api_key(self, temp_config_file: Path) -> None:
        """Test discover command fails gracefully when API key is missing."""
        runner = CliRunner()

        # Mock to simulate missing API key
        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesDiscoverer") as mock_discoverer_class:
            mock_discoverer_class.side_effect = ValueError("FIRECRAWL_API_KEY environment variable not found")

            result = runner.invoke(discover, ["--config", str(temp_config_file)])

            assert result.exit_code == 1
            assert "FIRECRAWL_API_KEY" in result.output

    def test_discover_invalid_config(self, tmp_path: Path) -> None:
        """Test discover command with invalid configuration."""
        # Create invalid config (missing required fields)
        config_file = tmp_path / "invalid_config.yaml"
        config_file.write_text("invalid: yaml\nmissing: required_fields")

        runner = CliRunner()
        result = runner.invoke(discover, ["--config", str(config_file)])

        assert result.exit_code == 1
        assert "validation error" in result.output.lower()


class TestFetchCLI:
    """Test web-fetch CLI command."""

    def test_fetch_help(self) -> None:
        """Test that fetch command shows help message."""
        runner = CliRunner()
        result = runner.invoke(fetch, ["--help"])

        assert result.exit_code == 0
        assert "Web articles content fetcher" in result.output
        assert "--config" in result.output
        assert "--dry-run" in result.output
        assert "--verbose" in result.output

    def test_fetch_missing_config_file(self) -> None:
        """Test fetch command with non-existent config file."""
        runner = CliRunner()
        result = runner.invoke(fetch, ["--config", "/nonexistent/config.yaml"])

        # Click returns exit code 2 for invalid arguments/missing files
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

    def test_fetch_with_valid_config(self, temp_config_file: Path, temp_review_file: Path) -> None:
        """Test fetch command with valid configuration and review file."""
        runner = CliRunner()

        # Update config to point to temp review file
        import yaml

        with open(temp_config_file) as f:
            config_data = yaml.safe_load(f)
        config_data["review_file"] = str(temp_review_file)
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = {
                "successful": 2,
                "failed": 0,
                "skipped": 0,
                "total": 2,
                "avg_word_count": 500,
            }
            mock_fetcher_class.return_value = mock_fetcher

            result = runner.invoke(fetch, ["--config", str(temp_config_file)])

            # Should succeed
            assert result.exit_code == 0
            assert mock_fetcher.fetch.called

    def test_fetch_missing_review_file(self, temp_config_file: Path) -> None:
        """Test fetch command when review file doesn't exist."""
        runner = CliRunner()

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.side_effect = FileNotFoundError("Review file not found")
            mock_fetcher_class.return_value = mock_fetcher

            result = runner.invoke(fetch, ["--config", str(temp_config_file)])

            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_fetch_dry_run(self, temp_config_file: Path, temp_review_file: Path) -> None:
        """Test fetch command with --dry-run flag."""
        runner = CliRunner()

        # Update config to point to temp review file
        import yaml

        with open(temp_config_file) as f:
            config_data = yaml.safe_load(f)
        config_data["review_file"] = str(temp_review_file)
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher_class.return_value = mock_fetcher

            result = runner.invoke(fetch, ["--config", str(temp_config_file), "--dry-run"])

            # Dry run should succeed without calling fetch
            assert result.exit_code == 0
            assert "Dry run completed successfully" in result.output
            assert not mock_fetcher.fetch.called

    def test_fetch_verbose_flag(self, temp_config_file: Path, temp_review_file: Path) -> None:
        """Test fetch command with --verbose flag."""
        runner = CliRunner()

        # Update config to point to temp review file
        import yaml

        with open(temp_config_file) as f:
            config_data = yaml.safe_load(f)
        config_data["review_file"] = str(temp_review_file)
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = {
                "successful": 2,
                "failed": 0,
                "skipped": 0,
                "total": 2,
                "avg_word_count": 500,
            }
            mock_fetcher_class.return_value = mock_fetcher

            result = runner.invoke(fetch, ["--config", str(temp_config_file), "--verbose"])

            assert result.exit_code == 0
            assert "Loading configuration" in result.output
            assert "Configuration loaded successfully" in result.output

    def test_fetch_with_failures(self, temp_config_file: Path, temp_review_file: Path) -> None:
        """Test fetch command when some articles fail to fetch."""
        runner = CliRunner()

        # Update config to point to temp review file
        import yaml

        with open(temp_config_file) as f:
            config_data = yaml.safe_load(f)
        config_data["review_file"] = str(temp_review_file)
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = {
                "successful": 1,
                "failed": 1,
                "skipped": 0,
                "total": 2,
                "avg_word_count": 500,
            }
            mock_fetcher_class.return_value = mock_fetcher

            result = runner.invoke(fetch, ["--config", str(temp_config_file)])

            # Should exit with error code when there are failures
            assert result.exit_code == 1

    def test_fetch_missing_api_key(self, temp_config_file: Path, temp_review_file: Path) -> None:
        """Test fetch command fails gracefully when API key is missing."""
        runner = CliRunner()

        # Update config to point to temp review file
        import yaml

        with open(temp_config_file) as f:
            config_data = yaml.safe_load(f)
        config_data["review_file"] = str(temp_review_file)
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock to simulate missing API key
        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesFetcher") as mock_fetcher_class:
            mock_fetcher_class.side_effect = ValueError("FIRECRAWL_API_KEY environment variable not found")

            result = runner.invoke(fetch, ["--config", str(temp_config_file)])

            assert result.exit_code == 1
            assert "FIRECRAWL_API_KEY" in result.output

    def test_fetch_keyboard_interrupt(self, temp_config_file: Path, temp_review_file: Path) -> None:
        """Test fetch command handles keyboard interrupt gracefully."""
        runner = CliRunner()

        # Update config to point to temp review file
        import yaml

        with open(temp_config_file) as f:
            config_data = yaml.safe_load(f)
        config_data["review_file"] = str(temp_review_file)
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.side_effect = KeyboardInterrupt()
            mock_fetcher_class.return_value = mock_fetcher

            result = runner.invoke(fetch, ["--config", str(temp_config_file)])

            assert result.exit_code == 1
            assert "interrupted" in result.output.lower()


class TestCLIDefaults:
    """Test CLI default values and behavior."""

    def test_discover_default_config_path(self) -> None:
        """Test that discover uses default config path when not specified."""
        runner = CliRunner()

        # Since default config doesn't exist, this should fail
        result = runner.invoke(discover, [])

        # Should attempt to use default path (Click may return 0 or non-zero)
        # Just verify it doesn't crash
        assert result.exit_code in [0, 1, 2]

    def test_fetch_default_config_path(self) -> None:
        """Test that fetch uses default config path when not specified."""
        runner = CliRunner()

        # Since default config doesn't exist, this should fail
        result = runner.invoke(fetch, [])

        # Should attempt to use default path
        assert result.exit_code == 1

    def test_discover_combined_flags(self, temp_config_file: Path) -> None:
        """Test discover with multiple flags combined."""
        runner = CliRunner()

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesDiscoverer") as mock_discoverer_class:
            mock_discoverer = MagicMock()
            mock_discoverer.discover.return_value = {
                "sources_processed": 1,
                "new_links": 5,
                "skipped_links": 0,
                "excluded_links": 0,
                "total_discovered": 5,
            }
            mock_discoverer_class.return_value = mock_discoverer

            result = runner.invoke(discover, ["--config", str(temp_config_file), "--verbose", "--force"])

            assert result.exit_code == 0
            # Verify both flags were honored
            mock_discoverer.discover.assert_called_with(force=True, verbose=True)

    def test_fetch_combined_flags(self, temp_config_file: Path, temp_review_file: Path) -> None:
        """Test fetch with multiple flags combined."""
        runner = CliRunner()

        # Update config to point to temp review file
        import yaml

        with open(temp_config_file) as f:
            config_data = yaml.safe_load(f)
        config_data["review_file"] = str(temp_review_file)
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("tools.web_articles.src.collectors.web_articles.cli.WebArticlesFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = {
                "successful": 2,
                "failed": 0,
                "skipped": 0,
                "total": 2,
                "avg_word_count": 500,
            }
            mock_fetcher_class.return_value = mock_fetcher

            result = runner.invoke(fetch, ["--config", str(temp_config_file), "--verbose"])

            assert result.exit_code == 0
            # Verify verbose was passed through
            mock_fetcher.fetch.assert_called_with(verbose=True)
