"""Command-line interface for Gmail collector.

This module provides the CLI entry point for the Gmail content collection tool.
"""

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from tools._shared.exceptions import AuthenticationFailureError, ContentProcessingError

from .collector import GmailCollector
from .config import load_gmail_config


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    default="settings/gmail.yaml",
    help="Path to YAML configuration file (default: settings/gmail.yaml)",
)
@click.option("--rule", "-r", help="Collect from specific rule only")
@click.option(
    "--dry-run", is_flag=True, help="Validate configuration and test Gmail API connection without processing emails"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--auth-only", is_flag=True, help="Only perform authentication setup without collecting emails")
def main(config: Path, rule: str | None, dry_run: bool, verbose: bool, auth_only: bool) -> None:
    """
    Gmail content collector for Signal system.

    Collects emails from configured Gmail rules, applying filters and saving
    content as organized markdown files with attachment support.

    Example usage:
        signal-gmail --config settings/gmail.yaml
        signal-gmail --config settings/gmail.yaml --rule "Important emails"
        signal-gmail --config settings/gmail.yaml --dry-run
        signal-gmail --config settings/gmail.yaml --auth-only
    """
    # If config is just a filename (no directory separator), look in settings/ folder
    if config.parent == Path('.'):
        config = Path('settings') / config

    # Validate that config file exists
    if not config.exists():
        click.echo(f"Error: Configuration file not found: {config}", err=True)
        sys.exit(1)

    try:
        # Set up logging
        if verbose:
            logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s", stream=sys.stdout)
        else:
            logging.basicConfig(level=logging.WARNING)

        # Load environment variables from .env file
        load_dotenv()

        # Load configuration
        if verbose:
            click.echo(f"Loading configuration from: {config}")

        gmail_config = load_gmail_config(str(config))

        if verbose:
            click.echo("Configuration loaded successfully:")
            click.echo(f"  Output directory: {gmail_config.output_dir}")
            click.echo(f"  Configured query rules: {len(gmail_config.rules)}")
            click.echo(f"  Configured label rules: {len(gmail_config.label_rules)}")
            click.echo(f"  Rate limit: {gmail_config.rate_limit_seconds} seconds")
            click.echo(f"  Token file: {gmail_config.token_file}")

        # Initialize collector
        if verbose:
            click.echo("Initializing Gmail collector...")

        collector = GmailCollector(gmail_config)

        if verbose:
            click.echo("Gmail API connection established successfully")

        # Auth-only mode - just set up authentication
        if auth_only:
            click.echo("✓ Authentication completed successfully")
            click.echo("✓ Gmail API access verified")
            click.echo(f"✓ Token saved to: {gmail_config.token_file}")
            click.echo("Authentication setup complete - you can now run collection commands")
            return

        # Dry run mode - just validate configuration and connection
        if dry_run:
            click.echo("✓ Configuration is valid")
            click.echo("✓ Gmail API connection successful")
            click.echo("✓ Output directory structure checked")

            if rule:
                # Find and validate specific rule
                rule_config = None
                for configured_rule in gmail_config.rules:
                    if configured_rule.name.lower() == rule.lower():
                        rule_config = configured_rule
                        break

                if rule_config:
                    click.echo(f"✓ Rule '{rule}' found in configuration")
                    click.echo(f"  Query: {rule_config.query}")
                    click.echo(f"  Max messages: {rule_config.max_messages}")
                    click.echo(f"  Actions: {rule_config.actions}")
                else:
                    click.echo(f"✗ Rule '{rule}' not found in configuration", err=True)
                    sys.exit(1)

            click.echo("Dry run completed successfully - no emails were processed or modified")
            return

        # Run collection
        if rule:
            # Collect from specific rule
            rule_config = None
            for configured_rule in gmail_config.rules:
                if configured_rule.name.lower() == rule.lower():
                    rule_config = configured_rule
                    break

            if not rule_config:
                click.echo(f"Error: Rule '{rule}' not found in configuration", err=True)
                sys.exit(1)

            if verbose:
                click.echo(f"Collecting from rule '{rule}' only...")

            stats = collector.collect_rule(rule_config)

            # Display results
            click.echo(f"\nCollection completed for rule '{rule}':")
            click.echo(f"  Messages processed: {stats['messages_processed']}")
            click.echo(f"  Messages saved: {stats['messages_saved']}")
            click.echo(f"  Messages skipped: {stats['messages_skipped']}")
            if stats["errors"] > 0:
                click.echo(click.style(f"  Errors: {stats['errors']}", fg="red"))

        else:
            # Collect from all configured rules
            if verbose:
                click.echo("Collecting from all configured rules...")

            overall_stats = collector.collect_all_rules()

            # Display results in consolidated format
            click.echo("\nCollection completed:")
            click.echo(f"  Query rules processed: {overall_stats['rules_processed']}")
            click.echo(f"  Label rules processed: {overall_stats['label_rules_processed']}")
            click.echo(f"  Total messages saved: {overall_stats['total_messages_saved']}")

            # Show per-rule action counts for query rules
            if overall_stats["rule_stats"]:
                for rule_stats in overall_stats["rule_stats"]:
                    click.echo(f"  Actions for '{rule_stats['rule']}': {rule_stats['actions_applied']}")

            # Show per-rule action counts for label rules
            if overall_stats.get("label_rule_stats"):
                for rule_stats in overall_stats["label_rule_stats"]:
                    click.echo(f"  Actions for label rule '{rule_stats['rule']}': {rule_stats['actions_applied']}")

            if overall_stats.get('total_trigger_labels_removed', 0) > 0:
                click.echo(f"  Trigger labels removed: {overall_stats['total_trigger_labels_removed']}")

            click.echo(f"  Total messages skipped: {overall_stats['total_messages_skipped']}")
            click.echo(f"  Total messages processed: {overall_stats['total_messages_processed']}")

            if overall_stats["total_actions_failed"] > 0:
                click.echo(click.style(f"  Total actions failed: {overall_stats['total_actions_failed']}", fg="yellow"))

            if overall_stats["total_errors"] > 0:
                click.echo(click.style(f"  Total errors: {overall_stats['total_errors']}", fg="red"))

            if verbose:
                click.echo("\nDetailed per-rule statistics:")

                # Query rules details
                if overall_stats["rule_stats"]:
                    click.echo("  Query Rules:")
                    for rule_stats in overall_stats["rule_stats"]:
                        click.echo(f"    {rule_stats['rule']}:")
                        click.echo(f"      Processed: {rule_stats['messages_processed']}")
                        click.echo(f"      Saved: {rule_stats['messages_saved']}")
                        click.echo(f"      Skipped: {rule_stats['messages_skipped']}")
                        click.echo(f"      Actions: {rule_stats['actions_applied']}")
                        if rule_stats["actions_failed"] > 0:
                            click.echo(click.style(f"      Actions failed: {rule_stats['actions_failed']}", fg="yellow"))
                        if rule_stats["errors"] > 0:
                            click.echo(f"      Errors: {rule_stats['errors']}")
                            if "error_message" in rule_stats:
                                click.echo(f"      Error: {rule_stats['error_message']}")

                # Label rules details
                if overall_stats.get("label_rule_stats"):
                    click.echo("  Label Rules:")
                    for rule_stats in overall_stats["label_rule_stats"]:
                        click.echo(f"    {rule_stats['rule']}:")
                        click.echo(f"      Processed: {rule_stats['messages_processed']}")
                        click.echo(f"      Saved: {rule_stats['messages_saved']}")
                        click.echo(f"      Skipped: {rule_stats['messages_skipped']}")
                        click.echo(f"      Actions: {rule_stats['actions_applied']}")
                        if rule_stats.get("trigger_labels_removed", 0) > 0:
                            click.echo(f"      Trigger labels removed: {rule_stats['trigger_labels_removed']}")
                        if rule_stats["actions_failed"] > 0:
                            click.echo(click.style(f"      Actions failed: {rule_stats['actions_failed']}", fg="yellow"))
                        if rule_stats["errors"] > 0:
                            click.echo(f"      Errors: {rule_stats['errors']}")
                            if "error_message" in rule_stats:
                                click.echo(f"      Error: {rule_stats['error_message']}")

    except FileNotFoundError as file_error:
        click.echo(f"Error: Configuration file not found: {file_error}", err=True)
        sys.exit(1)

    except ValueError as value_error:
        click.echo(f"Error: Configuration or authentication issue: {value_error}", err=True)
        sys.exit(1)

    except ContentProcessingError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    except AuthenticationFailureError as e:
        click.echo(f"Authentication Error: {e}", err=True)
        click.echo("\nRun 'signal-gmail --auth-only' to set up authentication", err=True)
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


if __name__ == "__main__":
    main()
