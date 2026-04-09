"""Command-line interface extensions for RAG Memory plugin.

Provides additional commands:
- setup: Interactive setup wizard
- install: Install dependencies (neural model)
- config: Configuration management
- reset: Reset database
- status: Quick health check
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click
import yaml
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


# ==============================================================================
# Utility Functions
# ==============================================================================


def get_hermes_home() -> Path:
    """Get Hermes home directory."""
    return Path.home() / ".hermes"


def get_plugin_dir() -> Path:
    """Get plugin directory."""
    return get_hermes_home() / "plugins" / "rag-memory"


def get_db_path() -> Path:
    """Get database path."""
    return get_plugin_dir() / "rag_core.db"


def get_config_path() -> Path:
    """Get config file path."""
    return get_plugin_dir() / "config.yaml"


def get_backup_dir() -> Path:
    """Get backup directory."""
    return get_plugin_dir() / "backups"


def check_sqlite_vec() -> bool:
    """Check if sqlite-vec is installed."""
    try:
        import sqlite_vec

        _ = sqlite_vec  # Mark as intentionally used
        return True
    except ImportError:
        return False


def check_neural_model() -> bool:
    """Check if neural model is available."""
    try:
        from sentence_transformers import SentenceTransformer

        # Try loading the model
        SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return True
    except Exception:
        return False


def install_sqlite_vec() -> bool:
    """Install sqlite-vec."""
    try:
        subprocess.run(
            ["pip", "install", "sqlite-vec"], check=True, capture_output=True, text=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def install_neural_dependencies() -> bool:
    """Install neural dependencies."""
    try:
        subprocess.run(
            ["pip", "install", "sentence-transformers"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def create_default_config() -> dict:
    """Create default configuration."""
    return {
        "database": {
            "path": str(get_db_path()),
            "backup_enabled": True,
            "backup_path": str(get_backup_dir()),
        },
        "search": {
            "max_results": 10,
            "default_mode": "hybrid",  # tfidf, neural, hybrid
            "threshold": 0.5,
        },
        "neural": {
            "enabled": True,
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "cache_dir": str(
                Path.home() / ".cache" / "torch" / "sentence_transformers"
            ),
        },
        "indexing": {
            "auto_index": True,
            "chunk_size": 500,
            "chunk_overlap": 50,
        },
    }


def load_config() -> dict:
    """Load configuration from file."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return create_default_config()


def save_config(config: dict) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def validate_database() -> tuple[bool, str]:
    """Validate database integrity."""
    db_path = get_db_path()
    if not db_path.exists():
        return False, "Database not found"

    try:
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Try to execute a simple query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        # Check for required tables
        required_tables = ["documents", "namespaces", "tfidf_terms", "metadata"]
        existing_tables = [t[0] for t in tables]

        missing_tables = set(required_tables) - set(existing_tables)
        if missing_tables:
            conn.close()
            return False, f"Missing tables: {missing_tables}"

        # Try to query documents table
        cursor.execute("SELECT COUNT(*) FROM documents")
        cursor.fetchone()

        conn.close()
        return True, "Database is valid"

    except sqlite3.DatabaseError as e:
        return False, f"Database corrupted: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


# ==============================================================================
# Setup Command
# ==============================================================================


@click.group()
def setup_cli():
    """Setup commands."""
    pass


@setup_cli.command()
@click.option(
    "--skip-prompts", is_flag=True, help="Run non-interactively with defaults"
)
@click.option("--reinit", is_flag=True, help="Force reinitialize database")
@click.option("--sqlite-vec", is_flag=True, help="Install sqlite-vec only")
@click.option("--neural", is_flag=True, help="Install neural model only")
def setup(skip_prompts: bool, reinit: bool, sqlite_vec: bool, neural: bool) -> None:
    """Interactive setup wizard for RAG Memory plugin."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    with console.status("[bold green]Initializing setup...", spinner="dots"):
        import time

        time.sleep(0.5)

    rprint(
        Panel.fit("[bold cyan]Welcome to RAG Memory Plugin Setup!", style="bold cyan")
    )
    print()

    # ==============================================================================
    # Step 1: Check existing installation
    # ==============================================================================
    console.print("[bold cyan]Step 1: Checking existing installation[/bold cyan]")
    print()

    db_path = get_db_path()
    config_path = get_config_path()

    if db_path.exists() and not reinit:
        rprint(
            Panel.fit(
                f"[yellow]⚠ Database already exists at:[/yellow]\n{db_path}",
                title="Existing Installation",
            )
        )

        if not skip_prompts and not Confirm.ask("Reinitialize database?"):
            console.print("[green]Keeping existing database[/green]")
        else:
            if not skip_prompts:
                if not Confirm.ask("This will DELETE all data. Continue?"):
                    console.print("[red]Setup aborted[/red]")
                    sys.exit(0)
            console.print("[yellow]Reinitializing database...[/yellow]")
            db_path.unlink()
    print()

    # ==============================================================================
    # Step 2: Database setup
    # ==============================================================================
    console.print("[bold cyan]Step 2: Database setup[/bold cyan]")
    print()

    plugin_dir = get_plugin_dir()
    if not plugin_dir.exists():
        console.print(f"Creating directory: {plugin_dir}")
        plugin_dir.mkdir(parents=True, exist_ok=True)
        console.print("[green]✓ Directory created[/green]")
    else:
        console.print("[green]✓ Directory exists[/green]")

    # Initialize database
    try:
        from rag_memory.core import RAGCore

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing database...", total=None)

            rag = RAGCore(str(db_path))

        console.print("[green]✓ Database initialized[/green]")
    except Exception as e:
        console.print(f"[red]✗ Database initialization failed:[/red] {e}")
        sys.exit(1)
    print()

    # ==============================================================================
    # Step 3: Dependency check
    # ==============================================================================
    console.print("[bold cyan]Step 3: Dependency check[/bold cyan]")
    print()

    # Check sqlite-vec
    has_sqlite_vec = check_sqlite_vec()
    if has_sqlite_vec:
        console.print("[green]✓ sqlite-vec is installed[/green]")
    else:
        console.print("[yellow]✗ sqlite-vec is not installed[/yellow]")
        if skip_prompts or sqlite_vec:
            console.print("Installing sqlite-vec...")
            if install_sqlite_vec():
                console.print("[green]✓ sqlite-vec installed[/green]")
            else:
                console.print("[red]✗ Failed to install sqlite-vec[/red]")
        else:
            if Confirm.ask("Install sqlite-vec?", default=True):
                if install_sqlite_vec():
                    console.print("[green]✓ sqlite-vec installed[/green]")
                else:
                    console.print("[red]✗ Failed to install sqlite-vec[/red]")
                    console.print("[yellow]Run: rag-memory setup sqlite-vec[/yellow]")
    print()

    # Check neural model
    has_neural = check_neural_model()
    if has_neural:
        console.print("[green]✓ Neural model is available[/green]")
    else:
        console.print("[yellow]✗ Neural model is not available[/yellow]")
        if skip_prompts or neural:
            console.print("Installing neural dependencies...")
            if install_neural_dependencies():
                console.print("[green]✓ Neural dependencies installed[/green]")
            else:
                console.print("[red]✗ Failed to install neural dependencies[/red]")
        else:
            if Confirm.ask("Install neural model? (recommended)", default=True):
                if install_neural_dependencies():
                    console.print("[green]✓ Neural dependencies installed[/green]")
                else:
                    console.print("[red]✗ Failed to install neural dependencies[/red]")
                    console.print(
                        "[yellow]You can install it later: rag-memory install neural[/yellow]"
                    )
                    console.print(
                        "[yellow]TF-IDF search will be used as fallback[/yellow]"
                    )
    print()

    # ==============================================================================
    # Step 4: Configuration
    # ==============================================================================
    console.print("[bold cyan]Step 4: Configuration[/bold cyan]")
    print()

    if config_path.exists():
        console.print(f"Current config: {config_path}")
        if not skip_prompts and not Confirm.ask("Modify configuration?", default=False):
            console.print("[green]Keeping existing configuration[/green]")
        else:
            # Load and show current config
            config = load_config()
            console.print("\n[cyan]Current configuration:[/cyan]")
            console.print(yaml.dump(config, default_flow_style=False))
    else:
        config = create_default_config()

    if not config_path.exists() or (
        not skip_prompts and Confirm.ask("Review configuration?", default=False)
    ):
        console.print("\n[cyan]Configuration options:[/cyan]")
        console.print("Press Enter for defaults\n")

        # Database path
        db_path_input = Prompt.ask(
            "Database path", default=str(config["database"]["path"])
        )
        config["database"]["path"] = db_path_input

        # Max results
        max_results = Prompt.ask(
            "Max search results", default=str(config["search"]["max_results"])
        )
        config["search"]["max_results"] = int(max_results)

        # Default mode
        mode = Prompt.ask(
            "Default search mode",
            choices=["tfidf", "neural", "hybrid"],
            default=config["search"]["default_mode"],
        )
        config["search"]["default_mode"] = mode

        # Neural enabled
        if check_neural_model():
            neural_enabled = Confirm.ask(
                "Enable neural search", default=config["neural"]["enabled"]
            )
            config["neural"]["enabled"] = neural_enabled

        # Save config
        save_config(config)
        console.print(f"\n[green]✓ Configuration saved to {config_path}[/green]")
    else:
        # Save default config if doesn't exist
        if not config_path.exists():
            save_config(create_default_config())
            console.print("[green]✓ Default configuration saved[/green]")
    print()

    # ==============================================================================
    # Step 5: Summary and confirmation
    # ==============================================================================
    console.print("[bold cyan]Setup Summary[/bold cyan]")
    print()

    table = Table(show_header=False, box=None)
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Database path", str(db_path))
    table.add_row("Config path", str(config_path))
    table.add_row(
        "sqlite-vec",
        (
            "[green]✓ Installed[/green]"
            if check_sqlite_vec()
            else "[red]✗ Not installed[/red]"
        ),
    )
    table.add_row(
        "Neural model",
        (
            "[green]✓ Available[/green]"
            if check_neural_model()
            else "[red]✗ Not available[/red]"
        ),
    )

    console.print(table)
    print()

    if not skip_prompts:
        if not Confirm.ask("Proceed with setup?", default=True):
            console.print("[red]Setup aborted[/red]")
            sys.exit(0)

    console.print("[green]✓ Setup complete![/green]")
    print()
    console.print("[cyan]Next steps:[/cyan]")
    console.print("  1. Run: rag-memory doctor")
    console.print('  2. Search: rag-memory search "your query"')
    print()


# ==============================================================================
# Install Neural Command
# ==============================================================================


@click.group()
def install_cli():
    """Install dependencies."""
    pass


@install_cli.command("neural")
@click.option("--force", is_flag=True, help="Reinstall even if already available")
def install_neural(force: bool) -> None:
    """Install neural search dependencies and model."""
    from rich.progress import (Progress,
                               SpinnerColumn, TextColumn)

    rprint(Panel.fit("[bold cyan]Neural Search Installation", style="bold cyan"))
    print()

    # Check if already available
    if not force and check_neural_model():
        console.print("[green]✓ Neural model is already available[/green]")
        print()
        console.print("[cyan]To reinstall, use:[/cyan]")
        console.print("  rag-memory install neural --force")
        return

    # Install dependencies
    console.print("[cyan]Step 1: Installing sentence-transformers...[/cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Installing package...", total=None)

            result = subprocess.run(
                ["pip", "install", "sentence-transformers"],
                check=True,
                capture_output=True,
                text=True,
            )

        console.print("[green]✓ sentence-transformers installed[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Installation failed:[/red] {e.stderr}")
        console.print("\n[yellow]Fallback:[/yellow] TF-IDF search will be used")
        console.print("[cyan]To retry later:[/cyan] rag-memory install neural")
        sys.exit(1)
    print()

    # Download model
    console.print("[cyan]Step 2: Downloading neural model...[/cyan]")
    console.print("[dim]This may take a few minutes on first run...[/dim]")
    print()

    try:
        from sentence_transformers import SentenceTransformer

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading model...", total=None)

            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        console.print("[green]✓ Model downloaded successfully[/green]")
    except Exception as e:
        console.print(f"[red]✗ Model download failed:[/red] {e}")
        console.print("\n[yellow]Fallback:[/yellow] TF-IDF search will be used")
        console.print("[cyan]To retry later:[/cyan] rag-memory install neural")
        console.print("\n[yellow]Possible causes:[/yellow]")
        console.print("  - Network connection issues")
        console.print("  - Insufficient disk space")
        console.print("  - Model repository unavailable")
        sys.exit(1)
    print()

    # Verify
    console.print("[cyan]Step 3: Verifying installation...[/cyan]")

    try:
        # Test encoding
        test_text = ["This is a test sentence."]
        embeddings = model.encode(test_text)

        console.print("[green]✓ Neural search is working![/green]")
        console.print(f"  Embedding dimension: {len(embeddings[0])}")
    except Exception as e:
        console.print(f"[red]✗ Verification failed:[/red] {e}")
        sys.exit(1)

    print()
    console.print("[bold green]Installation complete![/bold green]")
    console.print("\n[cyan]Neural search is now enabled.[/cyan]")


# ==============================================================================
# Config Command
# ==============================================================================


@click.group()
def config_cli():
    """Configuration management."""
    pass


@config_cli.command("show")
def config_show() -> None:
    """Show current configuration."""
    config_path = get_config_path()

    if not config_path.exists():
        console.print("[yellow]No configuration file found[/yellow]")
        console.print(f"Expected: {config_path}")
        console.print("\n[cyan]Run 'rag-memory setup' to create configuration[/cyan]")
        return

    config = load_config()

    rprint(Panel.fit("[bold cyan]Current Configuration", style="bold cyan"))
    print()
    console.print(yaml.dump(config, default_flow_style=False))


@config_cli.command("edit")
def config_edit() -> None:
    """Edit configuration in default editor."""
    config_path = get_config_path()

    if not config_path.exists():
        console.print("[yellow]No configuration file found[/yellow]")
        console.print(f"Expected: {config_path}")
        console.print("\n[cyan]Run 'rag-memory setup' to create configuration[/cyan]")
        return

    # Get editor
    editor = os.environ.get("EDITOR", "nano")

    console.print(f"[cyan]Opening {config_path} in {editor}...[/cyan]")
    print()

    try:
        subprocess.run([editor, str(config_path)], check=True)
        console.print("[green]✓ Configuration updated[/green]")

        # Validate
        console.print("\n[cyan]Validating configuration...[/cyan]")
        try:
            config = load_config()
            console.print("[green]✓ Configuration is valid[/green]")
        except Exception as e:
            console.print(f"[red]✗ Configuration error:[/red] {e}")
    except subprocess.CalledProcessError:
        console.print("[red]✗ Editor exited with error[/red]")


@config_cli.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value."""
    config_path = get_config_path()

    if not config_path.exists():
        console.print("[yellow]No configuration file found[/yellow]")
        console.print(f"Expected: {config_path}")
        console.print("\n[cyan]Run 'rag-memory setup' to create configuration[/cyan]")
        return

    try:
        config = load_config()

        # Parse key (e.g., "database.path" or "search.max_results")
        keys = key.split(".")
        current = config

        for k in keys[:-1]:
            if k not in current:
                console.print(f"[red]✗ Invalid key: {key}[/red]")
                return
            current = current[k]

        # Try to parse value as YAML (handles numbers, booleans, etc.)
        try:
            parsed_value = yaml.safe_load(value)
        except yaml.YAMLError:
            parsed_value = value

        current[keys[-1]] = parsed_value

        # Save
        save_config(config)

        console.print(f"[green]✓ Set {key} = {parsed_value}[/green]")

    except Exception as e:
        console.print(f"[red]✗ Failed to set value:[/red] {e}")


@config_cli.command("reset")
@click.option("--confirm", is_flag=True, help="Skip confirmation")
def config_reset(confirm: bool) -> None:
    """Reset configuration to defaults."""
    if not confirm:
        if not Confirm.ask("Reset configuration to defaults?", default=False):
            console.print("[yellow]Aborted[/yellow]")
            return

    default_config = create_default_config()
    save_config(default_config)

    console.print("[green]✓ Configuration reset to defaults[/green]")


@config_cli.command("validate")
def config_validate() -> None:
    """Validate configuration."""
    config_path = get_config_path()

    if not config_path.exists():
        console.print("[red]✗ Configuration file not found[/red]")
        console.print(f"Expected: {config_path}")
        sys.exit(1)

    try:
        config = load_config()

        # Check required keys
        required_keys = [
            ("database", "path"),
            ("search", "max_results"),
            ("neural", "enabled"),
        ]

        all_valid = True
        for key_path in required_keys:
            current = config
            for key in key_path:
                if key not in current:
                    console.print(
                        f"[red]✗ Missing required key: {'.'.join(key_path)}[/red]"
                    )
                    all_valid = False
                    break
                current = current[key]

        if all_valid:
            console.print("[green]✓ Configuration is valid[/green]")
        else:
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗ Validation error:[/red] {e}")
        sys.exit(1)


# ==============================================================================
# Status Command
# ==============================================================================


@click.command("status")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--quiet", is_flag=True, help="Exit code only, no output")
def status_cmd(json_output: bool, quiet: bool) -> None:
    """Quick health check."""
    if quiet:
        # Just check and exit
        db_path = get_db_path()
        if not db_path.exists():
            sys.exit(2)
        valid, _ = validate_database()
        sys.exit(0 if valid else 2)
        return

    if json_output:
        # JSON output
        db_path = get_db_path()
        is_valid, error = validate_database()

        status_info = {
            "status": "healthy" if is_valid else "unhealthy",
            "version": "1.0.0",
            "database": {
                "path": str(db_path),
                "exists": db_path.exists(),
                "valid": is_valid,
                "error": error if not is_valid else None,
            },
            "dependencies": {
                "sqlite_vec": check_sqlite_vec(),
                "neural_model": check_neural_model(),
            },
        }

        if db_path.exists():
            try:
                from rag_memory.core import RAGCore

                rag = RAGCore(str(db_path))
                stats = rag.get_stats()
                status_info["database"]["documents"] = stats.get("documents", 0)
                status_info["database"]["namespaces"] = stats.get("namespaces", 0)
            except:
                pass

        console.print(json.dumps(status_info, indent=2))
        return

    # Rich output
    rprint(Panel.fit("[bold cyan]RAG Memory Plugin - Status", style="bold cyan"))
    print()

    # Overall status
    db_path = get_db_path()
    is_valid, error = validate_database()

    if is_valid:
        console.print("[bold green]Status:[/bold green] [green]✓ Healthy[/green]")
    else:
        console.print("[bold red]Status:[/bold red] [red]✗ Unhealthy[/red]")
        console.print(f"  [red]{error}[/red]")
    print()

    # Database info
    if db_path.exists():
        console.print("[cyan]Database:[/cyan] [green]✓ OK[/green]")
        console.print(f"  Path: {db_path}")
        console.print(f"  Size: {db_path.stat().st_size / 1024 / 1024:.2f} MB")

        try:
            from rag_memory.core import RAGCore

            rag = RAGCore(str(db_path))
            stats = rag.get_stats()
            console.print(f"  Documents: {stats.get('documents', 0)}")
            console.print(f"  Namespaces: {stats.get('namespaces', 0)}")
        except Exception as e:
            console.print(f"  [yellow]⚠ Could not load stats: {e}[/yellow]")
    else:
        console.print("[cyan]Database:[/cyan] [red]✗ Not found[/red]")
    print()

    # Neural search
    console.print("[cyan]Neural Search:[/cyan]", end=" ")
    if check_neural_model():
        console.print("[green]✓ Enabled[/green]")
        console.print("  Model: sentence-transformers/all-MiniLM-L6-v2")
        console.print("  Status: Ready")
    else:
        console.print("[yellow]✗ Not available[/yellow]")
        console.print("  [dim]Run: rag-memory install neural[/dim]")
    print()

    # TF-IDF
    console.print("[cyan]TF-IDF Search:[/cyan]", end=" ")
    if check_sqlite_vec():
        console.print("[green]✓ Enabled[/green]")
        try:
            from rag_memory.core import RAGCore

            if db_path.exists():
                rag = RAGCore(str(db_path))
                stats = rag.get_stats()
                console.print(f"  Terms: {stats.get('tfidf_terms', 0):,}")
        except:
            pass
    else:
        console.print("[yellow]✗ Not available[/yellow]")
        console.print("  [dim]Run: rag-memory setup sqlite-vec[/dim]")
    print()

    # Config
    config_path = get_config_path()
    console.print("[cyan]Config:[/cyan]", end=" ")
    if config_path.exists():
        console.print("[green]✓ Valid[/green]")
        console.print(f"  Path: {config_path}")
    else:
        console.print("[yellow]✗ Not found[/yellow]")
        console.print("  [dim]Run: rag-memory setup[/dim]")

    print()
    sys.exit(0 if is_valid else 2)


# ==============================================================================
# Reset Command
# ==============================================================================


@click.command("reset")
@click.option("--force", is_flag=True, help="Skip confirmation")
@click.option("--no-backup", is_flag=True, help="Skip backup")
@click.option("--keep-config", is_flag=True, help="Keep configuration")
def reset_cmd(force: bool, no_backup: bool, keep_config: bool) -> None:
    """Reset database (DELETE ALL DATA)."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    rprint(
        Panel.fit(
            "[bold red]⚠️  DATABASE RESET[/bold red]",
            subtitle="[dim]This will DELETE all data[/dim]",
        )
    )
    print()

    db_path = get_db_path()

    if not db_path.exists():
        console.print("[yellow]Database does not exist[/yellow]")
        return

    # Show stats before reset
    try:
        from rag_memory.core import RAGCore

        rag = RAGCore(str(db_path))
        stats = rag.get_stats()

        console.print("[cyan]Current database:[/cyan]")
        console.print(f"  Documents: {stats.get('documents', 0)}")
        console.print(f"  Namespaces: {stats.get('namespaces', 0)}")
        print()
    except:
        pass

    # Confirmation
    if not force:
        console.print("[bold red]⚠️  This will DELETE all data![/bold red]")
        if not Confirm.ask("Are you sure?", default=False):
            console.print("[yellow]Aborted[/yellow]")
            return

        if not no_backup:
            if not Confirm.ask("Create backup before resetting?", default=True):
                no_backup = True

    # Backup
    if not no_backup:
        backup_dir = get_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"rag_core_backup_{timestamp}.db"

        console.print(f"\n[cyan]Creating backup:[/cyan] {backup_path}")
        shutil.copy2(db_path, backup_path)
        console.print("[green]✓ Backup created[/green]")
        print()

    # Delete database
    console.print("[cyan]Deleting database...[/cyan]")
    db_path.unlink()
    console.print("[green]✓ Database deleted[/green]")
    print()

    # Create fresh database
    console.print("[cyan]Creating fresh database...[/cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing...", total=None)

            from rag_memory.core import RAGCore

            rag = RAGCore(str(db_path))

        console.print("[green]✓ Fresh database created[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to create database:[/red] {e}")
        sys.exit(1)
    print()

    # Reset config if requested
    if not keep_config:
        config_path = get_config_path()
        if config_path.exists():
            console.print("[cyan]Resetting configuration...[/cyan]")
            config_path.unlink()
            console.print("[green]✓ Configuration reset[/green]")
            print()

    # Next steps
    console.print("[bold green]✓ Reset complete![/bold green]")
    print()
    console.print("[cyan]Next steps:[/cyan]")
    console.print("  1. Run: rag-memory setup")
    console.print("  2. Or restore from backup: rag-memory backup restore")
    print()


# Export commands for main CLI
__all__ = [
    "setup_cli",
    "install_cli",
    "config_cli",
    "status_cmd",
    "reset_cmd",
]
