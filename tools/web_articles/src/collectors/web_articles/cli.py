"""Command-line interface for web-articles collector.

This module provides CLI entry points for web article discovery and fetching.
"""

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from .collector import WebArticlesDiscoverer
from .config import load_web_articles_config
from .fetcher import WebArticlesFetcher


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default="settings/web-articles.yaml",
    help="Path to YAML configuration file (default: settings/web-articles.yaml)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate configuration and test Firecrawl API connection without saving files",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--force", is_flag=True, help="Re-discover all links (ignore state)")
def discover(config: Path, dry_run: bool, verbose: bool, force: bool) -> None:
    """Web articles link discovery collector.

    Crawls configured web sources to discover article links and generates
    a review file for human approval before fetching content.

    Example usage:
        web-discover
        web-discover --verbose
        web-discover --force --verbose
        web-discover --dry-run
    """
    # If config is just a filename (no directory separator), look in settings/ folder
    if config.parent == Path('.'):
        config = Path('settings') / config

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
            web_config = load_web_articles_config(str(config))
        except ValueError as config_error:
            click.echo(f"Configuration validation error: {config_error}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Configuration loaded successfully:")
            click.echo(f"  Output directory: {web_config.output_dir}")
            click.echo(f"  Configured sources: {len(web_config.sources)}")
            click.echo(f"  Rate limit: {web_config.rate_limit_seconds} seconds")
            click.echo(f"  Exclude keywords: {len(web_config.exclude_keywords)}")

        # Initialize discoverer
        if verbose:
            click.echo("Initializing web articles discoverer...")

        try:
            discoverer = WebArticlesDiscoverer(web_config)
        except ValueError as init_error:
            if "FIRECRAWL_API_KEY" in str(init_error):
                click.echo("FIRECRAWL_API_KEY not found in environment. Check your .env file.", err=True)
            else:
                click.echo(f"Discoverer initialization failed: {init_error}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Firecrawl API connection ready")

        # Dry run mode - just validate configuration
        if dry_run:
            click.echo("✓ Configuration is valid")
            click.echo("✓ Firecrawl API key found")
            click.echo("✓ Output directory structure checked")
            click.echo("Dry run completed successfully - no files were created or modified")
            return

        # Run discovery
        if verbose or True:  # Always show some output
            stats = discoverer.discover(force=force, verbose=True)
        else:
            stats = discoverer.discover(force=force, verbose=False)

        # Exit with appropriate code
        if stats["new_links"] == 0 and not force:
            sys.exit(0)  # Success, but no new links

    except FileNotFoundError:
        click.echo("Configuration file not found. Please check the path and try again.", err=True)
        sys.exit(1)

    except ValueError as value_error:
        click.echo(f"Configuration or validation error: {value_error}", err=True)
        sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\nDiscovery interrupted by user", err=True)
        sys.exit(1)

    except Exception as unexpected_error:
        click.echo("An unexpected error occurred during link discovery.", err=True)
        if verbose:
            click.echo(f"Error details: {unexpected_error}", err=True)
        sys.exit(1)


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default="settings/web-articles.yaml",
    help="Path to YAML configuration file (default: settings/web-articles.yaml)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate configuration and test Firecrawl API connection without saving files",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def fetch(config: Path, dry_run: bool, verbose: bool) -> None:
    """Web articles content fetcher.

    Reads the review file (approved links from discovery stage) and fetches
    full article content, saving as markdown files with frontmatter.

    Example usage:
        web-fetch
        web-fetch --verbose
        web-fetch --dry-run
    """
    # If config is just a filename (no directory separator), look in settings/ folder
    if config.parent == Path('.'):
        config = Path('settings') / config

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
            web_config = load_web_articles_config(str(config))
        except ValueError as config_error:
            click.echo(f"Configuration validation error: {config_error}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Configuration loaded successfully:")
            click.echo(f"  Output directory: {web_config.output_dir}")
            click.echo(f"  Rate limit: {web_config.rate_limit_seconds} seconds")

        # Initialize fetcher
        if verbose:
            click.echo("Initializing web articles fetcher...")

        try:
            fetcher = WebArticlesFetcher(web_config)
        except ValueError as init_error:
            if "FIRECRAWL_API_KEY" in str(init_error):
                click.echo("FIRECRAWL_API_KEY not found in environment. Check your .env file.", err=True)
            else:
                click.echo(f"Fetcher initialization failed: {init_error}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Firecrawl API connection ready")

        # Dry run mode - just validate
        if dry_run:
            # Check if review file exists
            import os

            review_file = web_config.review_file
            if not os.path.exists(review_file):
                click.echo(f"✗ {review_file} not found - run web-discover first", err=True)
                sys.exit(1)

            click.echo("✓ Configuration is valid")
            click.echo("✓ Firecrawl API key found")
            click.echo(f"✓ {review_file} exists")
            click.echo("Dry run completed successfully - no files were created or modified")
            return

        # Run fetch
        if verbose or True:  # Always show some output
            stats = fetcher.fetch(verbose=True)
        else:
            stats = fetcher.fetch(verbose=False)

        # Exit with appropriate code
        if stats["failed"] > 0:
            sys.exit(1)  # Some failures occurred

    except FileNotFoundError as fnf_error:
        click.echo(f"{fnf_error}", err=True)
        sys.exit(1)

    except ValueError as value_error:
        click.echo(f"Configuration or validation error: {value_error}", err=True)
        sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\nFetch interrupted by user", err=True)
        sys.exit(1)

    except Exception as unexpected_error:
        click.echo("An unexpected error occurred during content fetching.", err=True)
        if verbose:
            click.echo(f"Error details: {unexpected_error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    discover()
