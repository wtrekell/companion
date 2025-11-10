"""Command-line interface for web-direct collector.

This module provides CLI entry points for direct web content collection.
"""

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from .collector import WebDirectCollector
from .config import load_web_direct_config


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default="settings/web-direct.yaml",
    help="Path to YAML configuration file (default: settings/web-direct.yaml)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate configuration without fetching articles",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--force", is_flag=True, help="Re-fetch articles even if already in state")
def main(config: Path, dry_run: bool, verbose: bool, force: bool) -> None:
    """Web direct content collector.

    Discovers and fetches articles from configured index pages and saves as markdown
    files with frontmatter. Uses BeautifulSoup for link discovery and trafilatura
    for content extraction.

    Example usage:
        web-direct
        web-direct --verbose
        web-direct --force --verbose
        web-direct --dry-run
    """
    # If config is just a filename (no directory separator), look in settings/ folder
    if config.parent == Path("."):
        config = Path("settings") / config

    # Validate that config file exists
    if not config.exists():
        click.echo(f"Error: Configuration file not found: {config}", err=True)
        sys.exit(1)

    try:
        # Load environment variables from .env file
        load_dotenv()

        # Load configuration
        if verbose:
            click.echo(f"Loading configuration from: {config}")

        try:
            web_config = load_web_direct_config(str(config))
        except ValueError as config_error:
            click.echo(f"Configuration validation error: {config_error}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Configuration loaded successfully:")
            click.echo(f"  Output directory: {web_config.output_dir}")
            click.echo(f"  Configured sources: {len(web_config.sources)}")
            click.echo(f"  Rate limit: {web_config.rate_limit_seconds} seconds")
            click.echo(f"  Max retries: {web_config.max_retries}")
            click.echo(f"  Timeout: {web_config.timeout_seconds}s")

        # Dry run mode - just validate configuration
        if dry_run:
            click.echo("Configuration is valid")
            click.echo("Output directory structure checked")
            click.echo("Dry run completed successfully - no articles were fetched")
            return

        # Initialize collector
        if verbose:
            click.echo("Initializing web direct collector...")

        try:
            collector = WebDirectCollector(web_config)
        except ValueError as init_error:
            click.echo(f"Collector initialization failed: {init_error}", err=True)
            sys.exit(1)

        # Run collection
        stats = collector.collect(force=force, verbose=verbose)

        # Exit with appropriate code
        if stats["articles_failed"] > 0:
            sys.exit(1)  # Some failures occurred

    except FileNotFoundError:
        click.echo("Configuration file not found. Please check the path and try again.", err=True)
        sys.exit(1)

    except ValueError as value_error:
        click.echo(f"Configuration or validation error: {value_error}", err=True)
        sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\nCollection interrupted by user", err=True)
        sys.exit(1)

    except Exception as unexpected_error:
        click.echo("An unexpected error occurred during collection.", err=True)
        if verbose:
            click.echo(f"Error details: {unexpected_error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
