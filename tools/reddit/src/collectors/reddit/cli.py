"""Command-line interface for Reddit collector.

This module provides the CLI entry point for the Reddit content collection tool.
"""

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from tools._shared.security import sanitize_text_content

from .collector import RedditCollector
from .config import load_reddit_config


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default="settings/reddit.yaml",
    help="Path to YAML configuration file (default: settings/reddit.yaml)",
)
@click.option(
    "--subreddit",
    "-s",
    help="Collect from specific subreddit only",
    callback=lambda ctx, param, value: _validate_subreddit_name(value) if value else value,
)
@click.option(
    "--dry-run", is_flag=True, help="Validate configuration and test Reddit API connection without saving files"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def main(config: Path, subreddit: str | None, dry_run: bool, verbose: bool) -> None:
    """
    Reddit content collector for Signal system.

    Collects posts and comments from configured Reddit subreddits,
    applying filters and saving content as organized markdown files.

    Example usage:
        signal-reddit --config settings/reddit.yaml
        signal-reddit --config settings/reddit.yaml --subreddit Anthropic
        signal-reddit --config settings/reddit.yaml --dry-run
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
            reddit_config = load_reddit_config(str(config))
        except ValueError as config_error:
            click.echo(f"Configuration validation error: {config_error}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Configuration loaded successfully:")
            click.echo(f"  Output directory: {reddit_config.output_dir}")
            click.echo(f"  Configured subreddits: {len(reddit_config.subreddits)}")
            click.echo(f"  Rate limit: {reddit_config.rate_limit_seconds} seconds")

        # Initialize collector
        if verbose:
            click.echo("Initializing Reddit collector...")

        try:
            collector = RedditCollector(reddit_config)
        except ValueError as init_error:
            if "Reddit API" in str(init_error):
                click.echo("Reddit API authentication failed. Check your credentials.", err=True)
            else:
                click.echo(f"Collector initialization failed: {init_error}", err=True)
            sys.exit(1)
        except Exception as unexpected_error:
            click.echo("Unexpected initialization error occurred.", err=True)
            if verbose:
                click.echo(f"Details: {unexpected_error}", err=True)
            sys.exit(1)

        if verbose:
            click.echo("Reddit API connection established successfully")

        # Dry run mode - just validate configuration and connection
        if dry_run:
            click.echo("✓ Configuration is valid")
            click.echo("✓ Reddit API connection successful")
            click.echo("✓ Output directory structure checked")

            if subreddit:
                # Find and validate specific subreddit
                subreddit_config = None
                for sub_config in reddit_config.subreddits:
                    if sub_config.name.lower() == subreddit.lower():
                        subreddit_config = sub_config
                        break

                if subreddit_config:
                    click.echo(f"✓ Subreddit r/{subreddit} found in configuration")
                else:
                    click.echo(f"✗ Subreddit r/{subreddit} not found in configuration", err=True)
                    sys.exit(1)

            click.echo("Dry run completed successfully - no files were created or modified")
            return

        # Run collection
        if subreddit:
            # Collect from specific subreddit
            subreddit_config = None
            for sub_config in reddit_config.subreddits:
                if sub_config.name.lower() == subreddit.lower():
                    subreddit_config = sub_config
                    break

            if not subreddit_config:
                click.echo(f"Subreddit '{subreddit}' not found in configuration", err=True)
                sys.exit(1)

            if verbose:
                click.echo(f"Collecting from r/{subreddit} only...")

            try:
                stats = collector.collect_subreddit(subreddit_config)
            except Exception as collection_error:
                click.echo(f"Collection failed for r/{subreddit}", err=True)
                if verbose:
                    click.echo(f"Error details: {collection_error}", err=True)
                sys.exit(1)

            # Display results
            click.echo(f"\nCollection completed for r/{subreddit}:")
            click.echo(f"  Posts processed: {stats['posts_processed']}")
            click.echo(f"  Posts saved: {stats['posts_saved']}")
            click.echo(f"  Posts updated: {stats['posts_updated']}")
            click.echo(f"  Posts skipped: {stats['posts_skipped']}")
            if stats["errors"] > 0:
                click.echo(click.style(f"  Errors: {stats['errors']}", fg="red"))

        else:
            # Collect from all configured subreddits
            if verbose:
                click.echo("Collecting from all configured subreddits...")

            try:
                overall_stats = collector.collect_all_subreddits()
            except Exception as collection_error:
                click.echo("Collection failed", err=True)
                if verbose:
                    click.echo(f"Error details: {collection_error}", err=True)
                sys.exit(1)

            # Display results
            click.echo("\nCollection completed:")
            click.echo(f"  Subreddits processed: {overall_stats['subreddits_processed']}")
            click.echo(f"  Total posts processed: {overall_stats['total_posts_processed']}")
            click.echo(f"  Total posts saved: {overall_stats['total_posts_saved']}")
            click.echo(f"  Total posts updated: {overall_stats['total_posts_updated']}")
            click.echo(f"  Total posts skipped: {overall_stats['total_posts_skipped']}")
            if overall_stats["total_errors"] > 0:
                click.echo(click.style(f"  Total errors: {overall_stats['total_errors']}", fg="red"))

            if verbose:
                click.echo("\nPer-subreddit statistics:")
                for subreddit_stats in overall_stats["subreddit_stats"]:
                    click.echo(f"  r/{subreddit_stats['subreddit']}:")
                    click.echo(f"    Processed: {subreddit_stats['posts_processed']}")
                    click.echo(f"    Saved: {subreddit_stats['posts_saved']}")
                    click.echo(f"    Updated: {subreddit_stats['posts_updated']}")
                    click.echo(f"    Skipped: {subreddit_stats['posts_skipped']}")
                    if subreddit_stats["errors"] > 0:
                        click.echo(f"    Errors: {subreddit_stats['errors']}")

    except FileNotFoundError:
        click.echo("Configuration file not found. Please check the path and try again.", err=True)
        sys.exit(1)

    except ValueError as value_error:
        # Don't expose internal details - these are already sanitized by our validation
        click.echo(f"Configuration or authentication error: {value_error}", err=True)
        sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\nCollection interrupted by user", err=True)
        sys.exit(1)

    except Exception as unexpected_error:
        click.echo("An unexpected error occurred during Reddit collection.", err=True)
        if verbose:
            # Only show details in verbose mode, and sanitize sensitive information
            sanitized_error = sanitize_text_content(str(unexpected_error), max_length=500)
            click.echo(f"Error details: {sanitized_error}", err=True)
        sys.exit(1)


def _validate_subreddit_name(subreddit_name: str | None) -> str | None:
    """Validate subreddit name format to prevent injection attacks."""
    if not subreddit_name:
        return subreddit_name

    # Validate length
    if len(subreddit_name) > 21:
        raise click.BadParameter("Subreddit name cannot exceed 21 characters")

    # Validate characters (Reddit allows alphanumeric and underscore)
    import re

    if not re.match(r"^[a-zA-Z0-9_]+$", subreddit_name):
        raise click.BadParameter("Subreddit name can only contain letters, numbers, and underscores")

    # Prevent consecutive underscores and underscore at start/end
    if "__" in subreddit_name or subreddit_name.startswith("_") or subreddit_name.endswith("_"):
        raise click.BadParameter("Invalid subreddit name format")

    return subreddit_name


if __name__ == "__main__":
    main()
