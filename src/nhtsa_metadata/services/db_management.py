from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from nhtsa_metadata.config import sanitize_database_url


def inspect_database(database_url: str) -> dict[str, Any]:
    """Return a small local SQLite status report for DB management screens."""
    sqlite_path = sqlite_path_from_url(database_url)
    tables: dict[str, int] = {}
    if sqlite_path.exists():
        with sqlite3.connect(sqlite_path) as connection:
            table_names = [
                row[0]
                for row in connection.execute(
                    "select name from sqlite_master where type = 'table' order by name"
                ).fetchall()
            ]
            for table_name in table_names:
                tables[table_name] = int(
                    connection.execute(f'select count(*) from "{table_name}"').fetchone()[0]
                )
    return {
        "status": "ok" if sqlite_path.exists() else "missing",
        "database_url": sanitize_database_url(database_url),
        "dialect": "sqlite",
        "sqlite_path": str(sqlite_path),
        "exists": sqlite_path.exists(),
        "size_bytes": sqlite_path.stat().st_size if sqlite_path.exists() else 0,
        "table_count": len(tables),
        "tables": tables,
    }


def backup_database(database_url: str, output: Path) -> dict[str, Any]:
    """Create a SQLite backup without staging runtime DB artifacts."""
    sqlite_path = sqlite_path_from_url(database_url)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"database not found: {sqlite_path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as source, sqlite3.connect(output) as destination:
        source.backup(destination)
    return {
        "status": "ok",
        "source_path": str(sqlite_path),
        "backup_path": str(output),
        "size_bytes": output.stat().st_size,
    }


def vacuum_database(database_url: str, *, analyze: bool = True) -> dict[str, Any]:
    """Run local SQLite VACUUM/ANALYZE maintenance and return a GUI-friendly report."""
    sqlite_path = sqlite_path_from_url(database_url)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"database not found: {sqlite_path}")
    size_before = sqlite_path.stat().st_size
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("VACUUM")
        if analyze:
            connection.execute("ANALYZE")
    return {
        "status": "ok",
        "database_url": sanitize_database_url(database_url),
        "sqlite_path": str(sqlite_path),
        "vacuumed": True,
        "analyzed": analyze,
        "size_before_bytes": size_before,
        "size_after_bytes": sqlite_path.stat().st_size,
    }


def sqlite_path_from_url(database_url: str) -> Path:
    url = make_url(database_url)
    if url.drivername not in {"sqlite", "sqlite+pysqlite"}:
        raise ValueError(f"only sqlite database URLs are supported, got {url.drivername}")
    database_path = url.database
    if database_path is None or database_path in {"", ":memory:"}:
        raise ValueError("file-backed sqlite database URL is required")
    path = Path(database_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def copy_database_file(database_url: str, output: Path) -> dict[str, Any]:
    """Simple file copy helper for callers that explicitly do not need sqlite backup semantics."""
    sqlite_path = sqlite_path_from_url(database_url)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"database not found: {sqlite_path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sqlite_path, output)
    return {
        "status": "ok",
        "source_path": str(sqlite_path),
        "backup_path": str(output),
        "size_bytes": output.stat().st_size,
    }
