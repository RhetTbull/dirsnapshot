import importlib.metadata

__version__ = importlib.metadata.version("dirsnapshot")

from .dirsnapshot import (
    DirDiff,
    DirDiffResults,
    SnapshotInfo,
    is_snapshot_file,
    snapshot,
    snapshot_memory,
)

__all__ = [
    "DirDiff",
    "DirDiffResults",
    "is_snapshot_file",
    "snapshot_memory",
    "snapshot",
    "SnapshotInfo",
]
