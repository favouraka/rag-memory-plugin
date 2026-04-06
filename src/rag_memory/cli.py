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
    ✓ Database: /home/user/.hermes/plugins/rag-memory/rag_memory.db
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
        db_path = data_dir / "rag_memory.db"

        console.print(f"[cyan]Database:[/cyan] {db_path}")
        console.print(f"[cyan]Status:[/cyan] ", end="")

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
        db_path = data_dir / "rag_memory.db"

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
    new_db = data_dir / "rag_memory.db"

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
        rag = RAGCore(str(new_db))
        # RAGCore initializes automatically in __init__

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
        db_path = data_dir / "rag_memory.db"

        if not db_path.exists():
            console.print("[red]✗ Database not found[/red]")
            sys.exit(1)

        rag = RAGCore(str(db_path))

        # Get all documents
        documents = rag.get_all_documents(namespace=namespace)

        # Export to JSON
        with open(output, "w") as f:
            json.dump(documents, f, indent=2, default=str)

        console.print(f"[green]✓ Exported[/green] {len(documents)} documents to {output}")

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
        db_path = data_dir / "rag_memory.db"

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


if __name__ == "__main__":
    main()
