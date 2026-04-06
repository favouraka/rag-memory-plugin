"""Priority 3 CLI commands for RAG Memory plugin.

Provides advanced commands:
- backup: Backup management (create, list, restore, delete)
- migrate: Database migration
- recover: Automatic recovery from corruption
- index: File and directory indexing
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

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


def get_backup_dir() -> Path:
    """Get backup directory."""
    return get_plugin_dir() / "backups"


def list_backups() -> List[Path]:
    """List all backup files."""
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("rag_core_backup_*.db"), reverse=True)


def get_backup_info(backup_path: Path) -> dict:
    """Get backup information."""
    stat = backup_path.stat()
    db_info = {"path": backup_path, "size": stat.st_size, "modified": datetime.fromtimestamp(stat.st_mtime)}

    # Try to get document count from database
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        db_info["documents"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM namespaces")
        db_info["namespaces"] = cursor.fetchone()[0]

        conn.close()
    except Exception:
        db_info["documents"] = "?"
        db_info["namespaces"] = "?"

    return db_info


# ==============================================================================
# Backup Commands
# ==============================================================================

@click.group()
def backup_cli():
    """Backup management commands."""
    pass


@backup_cli.command('create')
@click.option('--description', '-d', help='Backup description')
def backup_create(description: str) -> None:
    """Create a database backup."""
    rprint(Panel.fit("[bold cyan]Creating Backup", style="bold cyan"))
    print()

    db_path = get_db_path()

    if not db_path.exists():
        console.print("[red]✗ Database not found[/red]")
        console.print(f"  Expected: {db_path}")
        sys.exit(1)

    # Create backup directory
    backup_dir = get_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Generate backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"rag_core_backup_{timestamp}.db"

    # If description provided, add it to filename
    if description:
        # Sanitize description (remove special chars, replace spaces with underscores)
        safe_desc = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in description)
        backup_path = backup_dir / f"rag_core_backup_{timestamp}_{safe_desc}.db"

    console.print(f"[cyan]Creating backup:[/cyan] {backup_path.name}")
    print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Copying database...", total=100)

            # Copy database
            shutil.copy2(db_path, backup_path)

            progress.update(task, completed=100)

        console.print("[green]✓ Backup created successfully[/green]")
        print()

        # Show backup info
        size_mb = backup_path.stat().st_size / 1024 / 1024
        console.print(f"[cyan]Location:[/cyan] {backup_path}")
        console.print(f"[cyan]Size:[/cyan] {size_mb:.2f} MB")

        # Get document count
        try:
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            docs = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM namespaces")
            namespaces = cursor.fetchone()[0]
            conn.close()

            console.print(f"[cyan]Documents:[/cyan] {docs}")
            console.print(f"[cyan]Namespaces:[/cyan] {namespaces}")
        except Exception:
            pass

    except Exception as e:
        console.print(f"[red]✗ Backup failed:[/red] {e}")
        sys.exit(1)


@backup_cli.command('list')
@click.option('--json', 'json_output', is_flag=True, help='JSON output')
def backup_list(json_output: bool) -> None:
    """List all backups."""
    backups = list_backups()

    if not backups:
        console.print("[yellow]No backups found[/yellow]")
        console.print(f"  Backup directory: {get_backup_dir()}")
        return

    if json_output:
        # JSON output
        backups_info = []
        for backup_path in backups:
            info = get_backup_info(backup_path)
            backups_info.append({
                "name": backup_path.name,
                "path": str(info["path"]),
                "size": info["size"],
                "modified": info["modified"].isoformat(),
                "documents": info.get("documents", 0),
                "namespaces": info.get("namespaces", 0),
            })

        console.print(json.dumps(backups_info, indent=2))
        return

    # Rich output
    rprint(Panel.fit("[bold cyan]Database Backups", style="bold cyan"))
    print()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Name", style="white")
    table.add_column("Size", style="green")
    table.add_column("Modified", style="yellow")
    table.add_column("Documents", style="cyan")
    table.add_column("Namespaces", style="cyan")

    for i, backup_path in enumerate(backups, 1):
        info = get_backup_info(backup_path)

        size_mb = info["size"] / 1024 / 1024
        modified_str = info["modified"].strftime("%Y-%m-%d %H:%M:%S")

        table.add_row(
            str(i),
            backup_path.name,
            f"{size_mb:.2f} MB",
            modified_str,
            str(info["documents"]),
            str(info["namespaces"]),
        )

    console.print(table)
    print()
    console.print(f"[cyan]Total backups:[/cyan] {len(backups)}")
    console.print(f"[cyan]Backup directory:[/cyan] {get_backup_dir()}")


@backup_cli.command('restore')
@click.argument('backup', type=click.Path(exists=True))
@click.option('--force', is_flag=True, help='Skip confirmation')
@click.option('--backup-current', is_flag=True, help='Backup current database before restoring')
def backup_restore(backup: str, force: bool, backup_current: bool) -> None:
    """Restore database from backup.

    BACKUP can be a filename or full path to backup file.
    """
    rprint(Panel.fit(
        "[bold yellow]⚠️  Database Restore[/bold yellow]",
        subtitle="[dim]This will REPLACE your current database[/dim]"
    ))
    print()

    # Resolve backup path
    backup_path = Path(backup)
    if not backup_path.is_absolute():
        # Try backup directory
        backup_path = get_backup_dir() / backup
        if not backup_path.exists():
            # Try as glob pattern
            matches = list(get_backup_dir().glob(f"*{backup}*"))
            if len(matches) == 1:
                backup_path = matches[0]
            elif len(matches) > 1:
                console.print("[yellow]Multiple backups found:[/yellow]")
                for m in matches:
                    console.print(f"  - {m.name}")
                console.print("\n[cyan]Please specify the exact filename.[/cyan]")
                sys.exit(1)
            else:
                console.print(f"[red]✗ Backup not found:[/red] {backup}")
                sys.exit(1)

    if not backup_path.exists():
        console.print(f"[red]✗ Backup not found:[/red] {backup_path}")
        sys.exit(1)

    # Get current database info
    db_path = get_db_path()

    if db_path.exists():
        try:
            from rag_memory.core import RAGCore
            rag = RAGCore(str(db_path))
            stats = rag.get_stats()

            console.print("[cyan]Current database:[/cyan]")
            console.print(f"  Path: {db_path}")
            console.print(f"  Documents: {stats.get('documents', 0)}")
            console.print(f"  Namespaces: {stats.get('namespaces', 0)}")
        except Exception:
            console.print("[cyan]Current database:[/cyan]")
            console.print(f"  Path: {db_path}")
            console.print("  [yellow]⚠ Could not read database info[/yellow]")
    else:
        console.print("[yellow]⚠ No current database found[/yellow]")

    print()

    # Get backup info
    backup_info = get_backup_info(backup_path)
    console.print("[cyan]Backup to restore:[/cyan]")
    console.print(f"  Path: {backup_path}")
    console.print(f"  Size: {backup_info['size'] / 1024 / 1024:.2f} MB")
    console.print(f"  Documents: {backup_info.get('documents', '?')}")
    console.print(f"  Namespaces: {backup_info.get('namespaces', '?')}")
    console.print(f"  Modified: {backup_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Confirmation
    if not force:
        if not Confirm.ask("Restore from this backup?", default=False):
            console.print("[yellow]Aborted[/yellow]")
            return

    # Backup current database if requested
    if backup_current and db_path.exists():
        console.print("\n[cyan]Creating backup of current database...[/cyan]")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        auto_backup_path = get_backup_dir() / f"rag_core_backup_{timestamp}_pre_restore.db"

        try:
            shutil.copy2(db_path, auto_backup_path)
            console.print(f"[green]✓ Backed up to:[/green] {auto_backup_path.name}")
        except Exception as e:
            console.print(f"[red]✗ Backup failed:[/red] {e}")
            if not Confirm.ask("Continue anyway?", default=False):
                sys.exit(1)

    print()

    # Restore backup
    console.print("[cyan]Restoring database...[/cyan]")

    try:
        # Create plugin directory if needed
        get_plugin_dir().mkdir(parents=True, exist_ok=True)

        # Copy backup to database location
        shutil.copy2(backup_path, db_path)

        console.print("[green]✓ Database restored successfully[/green]")
        print()

        # Verify
        console.print("[cyan]Verifying restored database...[/cyan]")
        from rag_memory.core import RAGCore
        rag = RAGCore(str(db_path))
        stats = rag.get_stats()

        console.print("[green]✓ Verification successful[/green]")
        console.print(f"  Documents: {stats.get('documents', 0)}")
        console.print(f"  Namespaces: {stats.get('namespaces', 0)}")

    except Exception as e:
        console.print(f"[red]✗ Restore failed:[/red] {e}")
        sys.exit(1)


@backup_cli.command('delete')
@click.argument('backup', type=click.Path())
@click.option('--force', is_flag=True, help='Skip confirmation')
def backup_delete(backup: str, force: bool) -> None:
    """Delete a backup.

    BACKUP can be a filename or full path to backup file.
    """
    # Resolve backup path
    backup_path = Path(backup)
    if not backup_path.is_absolute():
        # Try backup directory
        backup_path = get_backup_dir() / backup
        if not backup_path.exists():
            # Try as glob pattern
            matches = list(get_backup_dir().glob(f"*{backup}*"))
            if len(matches) == 1:
                backup_path = matches[0]
            elif len(matches) > 1:
                console.print("[yellow]Multiple backups found:[/yellow]")
                for m in matches:
                    console.print(f"  - {m.name}")
                console.print("\n[cyan]Please specify the exact filename.[/cyan]")
                sys.exit(1)
            else:
                console.print(f"[red]✗ Backup not found:[/red] {backup}")
                sys.exit(1)

    if not backup_path.exists():
        console.print(f"[red]✗ Backup not found:[/red] {backup_path}")
        sys.exit(1)

    # Show backup info
    backup_info = get_backup_info(backup_path)

    console.print("[yellow]Backup to delete:[/yellow]")
    console.print(f"  Name: {backup_path.name}")
    console.print(f"  Size: {backup_info['size'] / 1024 / 1024:.2f} MB")
    console.print(f"  Documents: {backup_info.get('documents', '?')}")
    console.print(f"  Modified: {backup_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Confirmation
    if not force:
        if not Confirm.ask("Delete this backup?", default=False):
            console.print("[yellow]Aborted[/yellow]")
            return

    # Delete
    try:
        backup_path.unlink()
        console.print("[green]✓ Backup deleted[/green]")
    except Exception as e:
        console.print(f"[red]✗ Delete failed:[/red] {e}")
        sys.exit(1)


# ==============================================================================
# Migrate Command
# ==============================================================================

@click.command('migrate')
@click.argument('source', type=click.Path(exists=True), required=False)
@click.option('--auto', is_flag=True, help='Auto-detect and migrate legacy database')
@click.option('--backup', is_flag=True, help='Create backup before migration')
def migrate_cmd(source: Optional[str], auto: bool, backup: bool) -> None:
    """Migrate data from another database.

    SOURCE: Path to source database file (SQLite .db file)

    If --auto is used, will try to find and migrate from legacy ~/rag-system location.
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

    # Determine source
    if auto:
        source = str(Path.home() / "rag-system" / "rag_data.db")
        console.print("[cyan]Auto-detecting legacy database...[/cyan]")
        console.print(f"  Looking for: {source}")

    if not source or not Path(source).exists():
        console.print("[red]✗ Source database not found[/red]")

        if auto:
            console.print("\n[cyan]To migrate manually:[/cyan]")
            console.print("  rag-memory migrate /path/to/old/database.db")
        else:
            console.print("\n[cyan]Usage:[/cyan]")
            console.print("  rag-memory migrate /path/to/database.db")
            console.print("  rag-memory migrate --auto")

        sys.exit(1)

    source_path = Path(source)
    db_path = get_db_path()

    console.print(f"\n[cyan]Source:[/cyan] {source_path}")
    console.print(f"[cyan]Destination:[/cyan] {db_path}")
    print()

    # Check if destination exists
    if db_path.exists():
        console.print("[yellow]⚠ Destination database already exists[/yellow]")

        if not Confirm.ask("Overwrite existing database?", default=False):
            console.print("[yellow]Aborted[/yellow]")
            return

        if backup:
            console.print("\n[cyan]Creating backup...[/cyan]")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = get_backup_dir() / f"rag_core_backup_{timestamp}_pre_migrate.db"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, backup_path)
            console.print(f"[green]✓ Backed up to:[/green] {backup_path.name}")
            print()

    # Try to connect to source database
    console.print("[cyan]Connecting to source database...[/cyan]")

    try:
        source_conn = sqlite3.connect(str(source_path))
        source_conn.row_factory = sqlite3.Row
        source_cursor = source_conn.cursor()

        # Check if it has documents table
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not source_cursor.fetchone():
            console.print("[red]✗ Source database doesn't have 'documents' table[/red]")
            console.print("[yellow]This doesn't look like a RAG database[/yellow]")
            source_conn.close()
            sys.exit(1)

        # Get count
        source_cursor.execute("SELECT COUNT(*) FROM documents")
        source_docs = source_cursor.fetchone()[0]

        console.print(f"[green]✓ Connected[/green]")
        console.print(f"  Documents: {source_docs}")

        source_conn.close()

    except Exception as e:
        console.print(f"[red]✗ Failed to connect:[/red] {e}")
        sys.exit(1)

    print()

    # Confirm migration
    if not Confirm.ask(f"Migrate {source_docs} documents?", default=True):
        console.print("[yellow]Aborted[/yellow]")
        return

    print()

    # Perform migration
    console.print("[cyan]Starting migration...[/cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Migrating...", total=100)

            # Create destination database
            from rag_memory.core import RAGCore
            dest_rag = RAGCore(str(db_path))

            progress.update(task, completed=20)

            # Connect to source
            source_conn = sqlite3.connect(str(source_path))
            source_conn.row_factory = sqlite3.Row
            source_cursor = source_conn.cursor()

            progress.update(task, completed=40)

            # Read all documents from source
            source_cursor.execute("SELECT * FROM documents")
            documents = source_cursor.fetchall()

            progress.update(task, completed=60)

            # Add to destination
            migrated = 0
            for doc in documents:
                dest_rag.add_document(
                    content=doc['content'],
                    namespace=doc.get('namespace', 'migrated'),
                    metadata=json.loads(doc.get('metadata', '{}')),
                )
                migrated += 1

                if migrated % 100 == 0:
                    progress.update(task, completed=60 + (migrated / len(documents) * 30))

            source_conn.close()

            progress.update(task, completed=100)

        console.print(f"\n[green]✓ Migration complete![/green]")
        console.print(f"  Migrated {migrated} documents")

    except Exception as e:
        console.print(f"\n[red]✗ Migration failed:[/red] {e}")
        sys.exit(1)


# ==============================================================================
# Recover Command
# ==============================================================================

@click.command('recover')
@click.option('--backup-corrupted', is_flag=True, help='Backup corrupted database before recovery')
@click.option('--from-backup', type=click.Path(exists=True), help='Restore from specific backup')
def recover_cmd(backup_corrupted: bool, from_backup: Optional[str]) -> None:
    """Automatic recovery from database corruption.

    Attempts to recover data from corrupted database by:
    1. Backing up corrupted database
    2. Creating fresh database
    3. Attempting data migration from backup

    If --from-backup is specified, will restore from that backup instead.
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn

    rprint(Panel.fit(
        "[bold red]⚠️  Database Recovery[/bold red]",
        subtitle="[dim]Attempting automatic recovery[/dim]"
    ))
    print()

    db_path = get_db_path()

    # If from-backup is specified, just restore it
    if from_backup:
        console.print(f"[cyan]Restoring from backup:[/cyan] {from_backup}")
        print()

        backup_path = Path(from_backup)
        if not backup_path.exists():
            console.print(f"[red]✗ Backup not found:[/red] {from_backup}")
            sys.exit(1)

        # Backup corrupted database if requested
        if backup_corrupted and db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            corrupted_backup = get_backup_dir() / f"rag_core_corrupted_{timestamp}.db"
            corrupted_backup.parent.mkdir(parents=True, exist_ok=True)

            console.print("[cyan]Backing up corrupted database...[/cyan]")
            try:
                shutil.copy2(db_path, corrupted_backup)
                console.print(f"[green]✓ Backed up to:[/green] {corrupted_backup.name}")
            except Exception as e:
                console.print(f"[red]✗ Backup failed:[/red] {e}")
                if not Confirm.ask("Continue anyway?", default=False):
                    sys.exit(1)
            print()

        # Restore from backup
        console.print("[cyan]Restoring from backup...[/cyan]")
        try:
            get_plugin_dir().mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, db_path)
            console.print("[green]✓ Database restored[/green]")

            # Verify
            from rag_memory.core import RAGCore
            rag = RAGCore(str(db_path))
            stats = rag.get_stats()
            console.print(f"  Documents: {stats.get('documents', 0)}")
            console.print(f"  Namespaces: {stats.get('namespaces', 0)}")

        except Exception as e:
            console.print(f"[red]✗ Restore failed:[/red] {e}")
            sys.exit(1)

        return

    # Check if database is actually corrupted
    if not db_path.exists():
        console.print("[yellow]⚠ Database not found[/yellow]")
        console.print("\n[cyan]Recovery options:[/cyan]")
        console.print("  1. Restore from backup:")
        console.print("     rag-memory recover --from-backup <backup_file>")
        console.print("  2. Or create fresh database:")
        console.print("     rag-memory setup")
        return

    # Try to validate database
    console.print("[cyan]Checking database integrity...[/cyan]")

    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Try a simple query
        cursor.execute("SELECT COUNT(*) FROM documents")
        cursor.fetchone()

        conn.close()

        console.print("[green]✓ Database appears to be valid[/green]")
        console.print("\n[yellow]⚠ No corruption detected[/yellow]")
        console.print("[cyan]If you're still experiencing issues, try:[/cyan]")
        console.print("  rag-memory doctor")
        return

    except sqlite3.DatabaseError as e:
        console.print(f"[red]✗ Database corrupted:[/red] {e}")
        print()

    except Exception as e:
        console.print(f"[red]✗ Database error:[/red] {e}")
        print()

    # Recovery steps
    console.print("[cyan]Recovery Plan:[/cyan]")
    print()

    console.print("1. Backup corrupted database")
    if not backup_corrupted:
        backup_corrupted = True

    console.print("2. Create fresh database")
    console.print("3. Attempt to migrate data from latest backup")
    print()

    if not Confirm.ask("Proceed with recovery?", default=True):
        console.print("[yellow]Aborted[/yellow]")
        return

    # Step 1: Backup corrupted database
    if backup_corrupted:
        console.print("\n[cyan]Step 1: Backing up corrupted database...[/cyan]")

        backup_dir = get_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        corrupted_backup = backup_dir / f"rag_core_corrupted_{timestamp}.db"

        try:
            shutil.copy2(db_path, corrupted_backup)
            console.print(f"[green]✓ Backed up to:[/green] {corrupted_backup.name}")
        except Exception as e:
            console.print(f"[red]✗ Backup failed:[/red] {e}")
            if not Confirm.ask("Continue anyway?", default=False):
                sys.exit(1)

    # Step 2: Create fresh database
    console.print("\n[cyan]Step 2: Creating fresh database...[/cyan]")

    try:
        db_path.unlink(missing_ok=True)

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

    # Step 3: Try to migrate from latest backup
    console.print("\n[cyan]Step 3: Attempting to restore from latest backup...[/cyan]")

    backups = list_backups()

    if backups:
        latest_backup = backups[0]
        console.print(f"[cyan]Latest backup:[/cyan] {latest_backup.name}")

        if Confirm.ask("Restore from this backup?", default=True):
            try:
                shutil.copy2(latest_backup, db_path)
                console.print("[green]✓ Database restored from backup[/green]")

                # Verify
                from rag_memory.core import RAGCore
                rag = RAGCore(str(db_path))
                stats = rag.get_stats()
                console.print(f"  Documents: {stats.get('documents', 0)}")
                console.print(f"  Namespaces: {stats.get('namespaces', 0)}")

            except Exception as e:
                console.print(f"[red]✗ Restore failed:[/red] {e}")
                console.print("[yellow]Fresh database created but data not restored[/yellow]")
    else:
        console.print("[yellow]⚠ No backups found[/yellow]")
        console.print("[yellow]Fresh database created but is empty[/yellow]")

    print()
    console.print("[green]✓ Recovery complete![/green]")
    print()
    console.print("[cyan]Next steps:[/cyan]")
    console.print("  1. Verify: rag-memory doctor")
    console.print("  2. Index files: rag-memory index-files")
    console.print("  3. Or restore from specific backup:")
    console.print("     rag-memory backup restore <backup_file>")


# ==============================================================================
# Index Command
# ==============================================================================

@click.command('index')
@click.argument('path', type=click.Path(exists=True))
@click.option('--namespace', default='indexed', help='Namespace for indexed documents')
@click.option('--chunk-size', default=500, help='Maximum characters per chunk')
@click.option('--force', is_flag=True, help='Re-index even if already indexed')
def index_cmd(path: str, namespace: str, chunk_size: int, force: bool) -> None:
    """Index a file or directory into the RAG database.

    PATH: Path to file or directory to index

    Examples:
      rag-memory index /path/to/file.md
      rag-memory index /path/to/directory/
      rag-memory index ~/Documents/notes.md --namespace personal
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

    target_path = Path(path).resolve()

    rprint(Panel.fit(
        f"[bold cyan]Indexing: {target_path.name}[/bold cyan]",
        subtitle=f"[dim]{target_path}[/dim]"
    ))
    print()

    # Initialize RAG
    db_path = get_db_path()

    if not db_path.exists():
        console.print("[red]✗ Database not found[/red]")
        console.print("\n[cyan]Run:[/cyan] rag-memory setup")
        sys.exit(1)

    from rag_memory.core import RAGCore

    try:
        rag = RAGCore(str(db_path))
    except Exception as e:
        console.print(f"[red]✗ Failed to load database:[/red] {e}")
        console.print("\n[cyan]Try:[/cyan] rag-memory recover")
        sys.exit(1)

    # Collect files to index
    files_to_index = []

    if target_path.is_file():
        files_to_index = [target_path]
    elif target_path.is_dir():
        # Find all markdown and text files
        for ext in ['*.md', '*.txt', '*.rst', '*.py', '*.js', '*.html', '*.css']:
            files_to_index.extend(target_path.rglob(ext))

    if not files_to_index:
        console.print("[yellow]⚠ No files found to index[/yellow]")
        return

    console.print(f"[cyan]Files to index:[/cyan] {len(files_to_index)}")
    print()

    # Index files
    from rag_memory.core.file_indexing import FileIndexer

    indexer = FileIndexer(str(db_path))

    indexed = 0
    skipped = 0
    errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing...", total=len(files_to_index))

        for file_path in files_to_index:
            try:
                # Read file
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if not content.strip():
                    skipped += 1
                    progress.update(task, advance=1)
                    continue

                # Check if already indexed
                if not force:
                    import hashlib
                    file_hash = hashlib.md5(content.encode()).hexdigest()

                    # Check if document with this hash exists
                    existing = rag.search(f"hash:{file_hash}", namespace=namespace, limit=1)
                    if existing:
                        skipped += 1
                        progress.update(task, advance=1)
                        continue

                # Index the file
                indexer.index_file(
                    file_path=str(file_path),
                    content=content,
                    namespace=namespace,
                    chunk_size=chunk_size,
                    metadata={
                        'source': 'file_index',
                        'file_path': str(file_path),
                        'file_name': file_path.name,
                        'indexed_at': datetime.now().isoformat(),
                    }
                )

                indexed += 1

            except Exception as e:
                errors.append(f"{file_path.name}: {str(e)}")

            progress.update(task, advance=1)

    # Print results
    console.print("\n[green]✓ Indexing complete[/green]")
    print()
    console.print(f"[cyan]Files indexed:[/cyan] {indexed}")
    console.print(f"[cyan]Files skipped:[/cyan] {skipped}")
    console.print(f"[cyan]Errors:[/cyan] {len(errors)}")

    if errors:
        print()
        console.print("[red]Errors:[/red]")
        for error in errors[:10]:
            console.print(f"  [red]✗[/red] {error}")
        if len(errors) > 10:
            console.print(f"  ... and {len(errors) - 10} more")


# Export commands for main CLI
__all__ = [
    'backup_cli',
    'migrate_cmd',
    'recover_cmd',
    'index_cmd',
]
