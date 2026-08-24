"""Checkpoint helpers for the SharePoint knowledge synchronization job.

The live Microsoft Graph and Azure AI Search adapters are intentionally wired
only in an environment-specific deployment layer. This module keeps the shared
repository contract limited to an opaque cursor and its timestamp.
"""

import os
from pathlib import Path

from app.connectors.base import SyncCheckpoint


def load_checkpoint(path: Path) -> SyncCheckpoint | None:
    """Load an opaque connector cursor, returning None before the first sync."""

    if not path.exists():
        return None
    return SyncCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))


def save_checkpoint(path: Path, checkpoint: SyncCheckpoint) -> None:
    """Atomically persist cursor metadata with owner-only file permissions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        checkpoint.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.chmod(0o600)
    os.replace(temporary_path, path)
