import importlib.metadata

__version__ = importlib.metadata.version("dirsnapshot")

from .dirsnapshot import (
    DirDiff,
    DirDiffResults,
    DirSnapshot,
    SnapshotInfo,
    SnapshotRecord,
    create_snapshot,
    create_snapshot_in_memory,
    is_snapshot_file,
    load_snapshot,
)

__all__ = [
    "create_snapshot_in_memory",
    "create_snapshot",
    "DirDiff",
    "DirDiffResults",
    "DirSnapshot" "is_snapshot_file",
    "load_snapshot",
    "SnapshotInfo",
    "SnapshotRecord",
]
