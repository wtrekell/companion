"""Command-line interface for StackExchange collector.

This module provides the CLI entry point for the StackExchange content collection tool.
"""

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from tools._shared.exceptions import ConfigurationValidationError, SecurityError
from tools._shared.security import sanitize_text_content, validate_input_length

from .collector import StackExchangeCollector
from .config import load_stackexchange_config


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default="settings/stackexchange.yaml",
    help="Path to YAML configuration file (default: settings/stackexchange.yaml)",
)
@click.option("--site", "-s", help="Collect from specific StackExchange site only")
@click.option("--dry-run", is_flag=True, help="Validate configuration and test API connection without saving files")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def main(config: Path, site: str | None, dry_run: bool, verbose: bool) -> None:
    """
    StackExchange content collector for Signal system.

    Collects questions, answers, and comments from configured StackExchange sites,
    applying filters and saving content as organized markdown files.

    Example usage:
        signal-stackexchange --config settings/stackexchange.yaml
        signal-stackexchange --config settings/stackexchange.yaml --site stackoverflow
        signal-stackexchange --config settings/stackexchange.yaml --dry-run
    """
    # If config is just a filename (no directory separator), look in settings/ folder
    if config.parent == Path('.'):
        config = Path('settings') / config

    # Validate that config file exists
    if not config.exists():
        click.echo(f"Error: Configuration file not found: {config}", err=True)
        sys.exit(1)

    try:
        # Validate and sanitize CLI inputs
        if site is not None:
            # Sanitize site name input
            site = sanitize_text_content(site.strip())
            site = validate_input_length(site, 100, "site name")

            if not site:
                click.echo("Error: Site name cannot be empty", err=True)
                sys.exit(1)

            # Additional validation for site name format
            import re

            if not re.match(r"^[a-zA-Z0-9.-]+$", site):
                click.echo(
                    "Error: Site name contains invalid characters. "
                    "Only letters, numbers, dots, and hyphens are allowed.",
                    err=True,
                )
                sys.exit(1)

        # Load environment variables from .env file
        load_dotenv()

        # Load configuration
        if verbose:
            click.echo(f"Loading configuration from: {config}")

        stackexchange_config = load_stackexchange_config(str(config))

        if verbose:
            click.echo("Configuration loaded successfully:")
            click.echo(f"  Output directory: {stackexchange_config.output_dir}")
            click.echo(f"  Configured sites: {len(stackexchange_config.sites)}")
            click.echo(f"  Rate limit: {stackexchange_config.rate_limit_seconds} seconds")
            if stackexchange_config.api_key:
                click.echo("  API key: configured (higher quotas available)")
            else:
                click.echo("  API key: not configured (using default quotas)")

        # Initialize collector with context manager to ensure resource cleanup
        if verbose:
            click.echo("Initializing StackExchange collector...")

        with StackExchangeCollector(stackexchange_config) as collector:
            if verbose:
                click.echo("StackExchange API connection initialized successfully")

            # Dry run mode - just validate configuration and connection
            if dry_run:
                click.echo("✓ Configuration is valid")
                click.echo("✓ StackExchange API connection initialized")
                click.echo("✓ Output directory structure checked")

                if site:
                    # Find and validate specific site
                    site_config = None
                    for site_cfg in stackexchange_config.sites:
                        if site_cfg.name.lower() == site.lower():
                            site_config = site_cfg
                            break

                    if site_config:
                        click.echo(f"✓ StackExchange site '{site}' found in configuration")
                        if site_config.tags:
                            click.echo(f"  - Tags: {', '.join(site_config.tags)}")
                        click.echo(f"  - Max questions: {site_config.max_questions}")
                        click.echo(f"  - Include answers: {site_config.include_answers}")
                        click.echo(f"  - Include comments: {site_config.include_comments}")
                    else:
                        click.echo(f"✗ StackExchange site '{site}' not found in configuration", err=True)
                        available_sites = [s.name for s in stackexchange_config.sites]
                        click.echo(f"Available sites: {', '.join(available_sites)}", err=True)
                        sys.exit(1)

                click.echo("Dry run completed successfully - no files were created or modified")
                return

            # Run collection
            if site:
                # Collect from specific site
                site_config = None
                for site_cfg in stackexchange_config.sites:
                    if site_cfg.name.lower() == site.lower():
                        site_config = site_cfg
                        break

                if not site_config:
                    click.echo(f"Error: StackExchange site '{site}' not found in configuration", err=True)
                    available_sites = [s.name for s in stackexchange_config.sites]
                    click.echo(f"Available sites: {', '.join(available_sites)}", err=True)
                    sys.exit(1)

                if verbose:
                    click.echo(f"Collecting from {site} only...")

                stats = collector.collect_site(site_config)

                # Display results
                click.echo(f"\nCollection completed for {site}:")
                click.echo(f"  Questions processed: {stats['questions_processed']}")
                click.echo(f"  Questions saved: {stats['questions_saved']}")
                click.echo(f"  Questions updated: {stats['questions_updated']}")
                click.echo(f"  Questions skipped: {stats['questions_skipped']}")
                if stats["errors"] > 0:
                    click.echo(click.style(f"  Errors: {stats['errors']}", fg="red"))

            else:
                # Collect from all configured sites
                if verbose:
                    click.echo("Collecting from all configured StackExchange sites...")

                overall_stats = collector.collect_all_sites()

                # Display results
                click.echo("\nCollection completed:")
                click.echo(f"  Sites processed: {overall_stats['sites_processed']}")
                click.echo(f"  Total questions processed: {overall_stats['total_questions_processed']}")
                click.echo(f"  Total questions saved: {overall_stats['total_questions_saved']}")
                click.echo(f"  Total questions updated: {overall_stats['total_questions_updated']}")
                click.echo(f"  Total questions skipped: {overall_stats['total_questions_skipped']}")
                if overall_stats["total_errors"] > 0:
                    click.echo(click.style(f"  Total errors: {overall_stats['total_errors']}", fg="red"))

                if verbose:
                    click.echo("\nPer-site statistics:")
                    for site_stats in overall_stats["site_stats"]:
                        click.echo(f"  {site_stats['site']}:")
                        click.echo(f"    Processed: {site_stats['questions_processed']}")
                        click.echo(f"    Saved: {site_stats['questions_saved']}")
                        click.echo(f"    Updated: {site_stats['questions_updated']}")
                        click.echo(f"    Skipped: {site_stats['questions_skipped']}")
                        if site_stats["errors"] > 0:
                            click.echo(f"    Errors: {site_stats['errors']}")

    except FileNotFoundError as file_error:
        click.echo(f"Error: Configuration file not found: {file_error}", err=True)
        sys.exit(1)

    except ConfigurationValidationError as config_error:
        click.echo(f"Error: Configuration validation failed: {config_error}", err=True)
        sys.exit(1)

    except SecurityError as security_error:
        click.echo(f"Error: Security validation failed: {security_error}", err=True)
        click.echo("Please check your configuration for potential security issues.", err=True)
        sys.exit(1)

    except ValueError as value_error:
        click.echo(f"Error: Configuration issue: {value_error}", err=True)
        sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\nCollection interrupted by user", err=True)
        sys.exit(1)

    except Exception as unexpected_error:
        click.echo(f"Unexpected error: {unexpected_error}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
    # Note: Resource cleanup handled automatically by context manager (__exit__ method)


if __name__ == "__main__":
    main()
