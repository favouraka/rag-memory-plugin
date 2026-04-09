"""Command-line interface for RAG Memory plugin.

Provides commands for:
- doctor: Health check and diagnostics
- migrate: Migrate data from legacy ~/rag-system
- stats: Show database statistics
- search: Query the RAG database
- export: Export data to JSON
- import: Import data from JSON

Example
-------
.. code-block:: bash

    $ rag-memory doctor
    ✓ Database: /home/user/.hermes/plugins/rag-memory/rag_core.db
    ✓ Documents: 168
    ✓ Embeddings: 168
    ✓ Mode: hybrid

    $ rag-memory search "AI agent"
    [1] 0.89 "Hermes is an AI agent that..."
    [2] 0.75 "Another agent system..."
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="rag-memory")
def main() -> None:
    """RAG Memory - Production-grade retrieval for Hermes Agent."""
    pass


@main.command()
def doctor() -> None:
    """Health check and diagnostics."""
    try:
        from rag_memory.core import RAGCore

        hermes_home = Path.home() / ".hermes"
        data_dir = hermes_home / "plugins" / "rag-memory"
        db_path = data_dir / "rag_core.db"

        console.print(f"[cyan]Database:[/cyan] {db_path}")
        console.print("[cyan]Status:[/cyan] ", end="")

        if not db_path.exists():
            console.print("[red]✗ Not found[/red]")
            console.print("\n[yellow]Run:[/yellow] rag-memory migrate-from-legacy")
            sys.exit(1)

        # Load and check
        rag = RAGCore(str(db_path))
        stats = rag.get_stats()

        console.print("[green]✓ OK[/green]")

        # Print stats table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        for key, value in stats.items():
            table.add_row(key.replace("_", " ").title(), str(value))

        console.print("\n")
        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)


@main.command()
@click.argument("query")
@click.option("--namespace", default=None, help="Namespace to search")
@click.option("--limit", default=5, help="Max results")
def search(query: str, namespace: str | None, limit: int) -> None:
    """Search the RAG database."""
    try:
        from rag_memory.core import RAGCore

        hermes_home = Path.home() / ".hermes"
        data_dir = hermes_home / "plugins" / "rag-memory"
        db_path = data_dir / "rag_core.db"

        if not db_path.exists():
            console.print("[red]✗ Database not found[/red]")
            console.print("\n[yellow]Run:[/yellow] rag-memory migrate-from-legacy")
            sys.exit(1)

        rag = RAGCore(str(db_path))
        results = rag.search(query, namespace=namespace, limit=limit)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Score", style="green", width=8)
        table.add_column("Content", style="white")

        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            content = result.get("content", "")[:80]
            table.add_row(str(i), f"{score:.2f}", content)

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        sys.exit(1)


@main.command()
def migrate_from_legacy() -> None:
    """Migrate data from legacy ~/rag-system installation."""
    console.print("[cyan]Migrating from legacy ~/rag-system...[/cyan]\n")

    legacy_db = Path.home() / "rag-system" / "rag_data.db"
    hermes_home = Path.home() / ".hermes"
    data_dir = hermes_home / "plugins" / "rag-memory"
    new_db = data_dir / "rag_core.db"

    if not legacy_db.exists():
        console.print("[yellow]✗ Legacy database not found[/yellow]")
        console.print(f"  Expected: {legacy_db}")
        sys.exit(1)

    if new_db.exists():
        console.print("[yellow]⚠ New database already exists[/yellow]")
        if not click.confirm("Overwrite?", default=False):
            console.print("[red]Aborted[/red]")
            sys.exit(1)

    try:
        from rag_memory.core import RAGCore

        # Create data directory
        data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize new database
        RAGCore(str(new_db))  # Initialize and create database

        console.print(f"[cyan]Legacy DB:[/cyan] {legacy_db}")
        console.print(f"[cyan]New DB:[/cyan] {new_db}")

        # TODO: Implement actual migration
        # This would connect to legacy DB, export data, import to new DB
        console.print("\n[yellow]⚠ Migration not yet implemented[/yellow]")
        console.print("[cyan]See:[/cyan] scripts/migrate_legacy.py")

    except Exception as e:
        console.print(f"[red]✗ Migration failed:[/red] {e}")
        sys.exit(1)


@main.command()
@click.argument("output", type=click.Path(path_type=Path))
@click.option("--namespace", default=None, help="Export specific namespace")
def export(output: Path, namespace: str | None) -> None:
    """Export RAG database to JSON."""
    try:
        from rag_memory.core import RAGCore

        hermes_home = Path.home() / ".hermes"
        data_dir = hermes_home / "plugins" / "rag-memory"
        db_path = data_dir / "rag_core.db"

        if not db_path.exists():
            console.print("[red]✗ Database not found[/red]")
            sys.exit(1)

        rag = RAGCore(str(db_path))

        # Get all documents
        documents = rag.get_all_documents(namespace=namespace)

        # Export to JSON
        with open(output, "w") as f:
            json.dump(documents, f, indent=2, default=str)

        console.print(
            f"[green]✓ Exported[/green] {len(documents)} documents to {output}"
        )

    except Exception as e:
        console.print(f"[red]✗ Export failed:[/red] {e}")
        sys.exit(1)


@main.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
def import_data(input: Path) -> None:
    """Import documents from JSON to RAG database."""
    try:
        from rag_memory.core import RAGCore

        hermes_home = Path.home() / ".hermes"
        data_dir = hermes_home / "plugins" / "rag-memory"
        db_path = data_dir / "rag_core.db"

        # Initialize if needed
        rag = RAGCore(str(db_path))
        if not db_path.exists():
            # RAGCore initializes automatically in __init__
            pass

        # Load JSON
        with open(input) as f:
            documents = json.load(f)

        # Import
        added = 0
        for doc in documents:
            rag.add_document(
                content=doc.get("content", ""),
                namespace=doc.get("namespace", "imported"),
                metadata=doc.get("metadata", {}),
            )
            added += 1

        console.print(f"[green]✓ Imported[/green] {added} documents from {input}")

    except Exception as e:
        console.print(f"[red]✗ Import failed:[/red] {e}")
        sys.exit(1)


@main.command()
@click.option("--namespace", default=None, help="Namespace to search (default: all)")
@click.option(
    "--pattern", multiple=True, help="File patterns to index (can use multiple)"
)
@click.option("--chunk-size", default=2000, help="Maximum characters per chunk")
@click.option("--force", is_flag=True, help="Re-index all files (skip deduplication)")
def index_files(
    namespace: str | None, pattern: tuple, chunk_size: int, force: bool
) -> None:
    """Index Hermes memory files into RAG database.

    Indexes MEMORY.md, skills, tool docs, and other static knowledge files
    for semantic search during conversations.

    Example:

    \t rag-memory index-files

    \t rag-memory index-files --pattern "MEMORY.md" --pattern "SESSION-STATE.md"

    \t rag-memory index-files --force --chunk-size 3000
    """
    try:
        from rag_memory.core import RAGCore, index_hermes_files

        hermes_home = Path.home() / ".hermes"
        data_dir = hermes_home / "plugins" / "rag-memory"
        db_path = data_dir / "rag_core.db"

        if not db_path.exists():
            console.print("[red]✗ Database not found[/red]")
            console.print("\n[yellow]Run:[/yellow] rag-memory doctor")
            sys.exit(1)

        console.print(f"[cyan]Hermes home:[/cyan] {hermes_home}")

        # Build patterns if provided
        patterns = None
        if pattern:
            patterns = {"custom": list(pattern)}
            console.print(f"[cyan]Patterns:[/cyan] {patterns}")

        # Initialize RAG
        rag = RAGCore(str(db_path))

        # Index files
        with console.status("[bold green]Indexing files...", spinner="dots"):
            stats = index_hermes_files(
                rag,
                hermes_home=hermes_home,
                patterns=patterns,
                chunk_size=chunk_size,
            )

        # Print results
        console.print("\n[green]✓ Indexing complete[/green]")
        console.print(f"\n[cyan]Files scanned:[/cyan] {stats['files_scanned']}")
        console.print(f"[cyan]Files indexed:[/cyan] {stats['files_indexed']}")
        console.print(f"[cyan]Chunks added:[/cyan] {stats['chunks_added']}")

        if stats["chunks_skipped"] > 0:
            console.print(
                f"[yellow]Chunks skipped (duplicates):[/yellow] {stats['chunks_skipped']}"
            )

        if stats["errors"]:
            console.print(f"\n[red]Errors:[/red] {len(stats['errors'])}")
            for error in stats["errors"][:5]:
                console.print(f"  [red]✗[/red] {error}")

    except Exception as e:
        console.print(f"[red]✗ Indexing failed:[/red] {e}")
        sys.exit(1)


# Import extended commands (imported here to avoid circular imports)  # noqa: E402
from .cli_extended import (config_cli, install_cli, reset_cmd, setup_cli,
                           status_cmd)
# Import Priority 3 commands (imported here to avoid circular imports)  # noqa: E402
from .cli_priority3 import backup_cli, index_cmd, migrate_cmd, recover_cmd

# Add extended commands to main group
main.add_command(setup_cli, name="setup")
main.add_command(install_cli, name="install")
main.add_command(config_cli, name="config")
main.add_command(status_cmd, name="status")
main.add_command(reset_cmd, name="reset")

# Add Priority 3 commands
main.add_command(backup_cli, name="backup")
main.add_command(migrate_cmd, name="migrate")
main.add_command(recover_cmd, name="recover")
main.add_command(index_cmd, name="index")


if __name__ == "__main__":
    main()
