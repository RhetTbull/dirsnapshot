"""Report differences between a directory and a previous snapshot of the same directory. 

This works very similar to [dircmp](https://docs.python.org/3/library/filecmp.html#the-dircmp-class) 
but it is designed to be used with a directory that is being monitored instead of comparing two 
existing directories.

This module can be run as a standalone CLI app or included in your project as a module.
"""

import datetime
import importlib.metadata
import json
import os
import sqlite3
from collections import namedtuple
from os import stat as osstat
from os import walk as oswalk
from os.path import exists as pathexists
from os.path import join as joinpath
from typing import Callable, Dict, Optional, Tuple

# Note: os.stat, os.walk, os.path.exists, os.path.join are imported as separate names
# because this increases performance slightly and these will be called repeatedly to
# create the snapshot

__version__ = importlib.metadata.version("dirsnapshot")

__all__ = [
    "DirDiff",
    "DirDiffResults",
    "is_snapshot_file",
    "snapshot_memory",
    "snapshot",
    "SnapshotInfo",
]

METADATA_SOURCE = "dirsnapshot"
METADATA_DESCRIPTION = "Directory Snapshot created by dirsnapshot"

DirDiffResults = namedtuple(
    "DirDiffResults", ["added", "removed", "modified", "identical"]
)

SnapshotInfo = namedtuple("SnapshotInfo", ["description", "directory", "datetime"])


def snapshot(
    dirpath: str,
    snapshot_db: str,
    walk: bool = True,
    description: Optional[str] = None,
    filter_function: Optional[Callable[[str], bool]] = None,
) -> None:
    """Create a snapshot of a directory

    Args:
        dir: path to directory to snapshot
        snapshot_db: path to database to write snapshot to
        walk: if True, walk the directory tree and add all files and directories
        description: optional description of the snapshot
        filter: optional function to filter out files and directories; should return True if the file or directory should be included in the snapshot

    Raises:
        ValueError if snapshot_db already exists
    """

    if pathexists(snapshot_db):
        raise ValueError(f"Snapshot database {snapshot_db} already exists")

    conn, cursor = _open_snapshot_db(snapshot_db, dirpath, description)
    _snapshot(dirpath, walk, conn, cursor, filter_function)


def snapshot_memory(
    dirpath: str,
    walk: bool = True,
    description: Optional[str] = None,
    filter_function: Optional[Callable[[str], bool]] = None,
) -> sqlite3.Connection:
    """Create a snapshot of a directory in memory

    Args:
        dir: path to directory to snapshot
        walk: if True, walk the directory tree and add all files and directories
        description: optional description of the snapshot

    Returns:
        sqlite3.Connection to in-memory database
    """

    conn, cursor = _open_snapshot_db(":memory:", description)
    _snapshot(dirpath, walk, conn, cursor, filter_function)
    return conn


def _snapshot(
    dirpath: str,
    walk: bool,
    conn: sqlite3.Connection,
    cursor: sqlite3.Cursor,
    filter_function: Callable[[str], bool] = None,
):
    for current_dirpath, dirnames, filenames in oswalk(dirpath):
        for dirname in dirnames:
            pathstr = joinpath(current_dirpath, dirname)
            if filter_function and not filter_function(pathstr):
                continue
            statinfo = osstat(pathstr)
            _add_snapshot_db_entry(
                cursor, pathstr, statinfo, is_dir=True, is_file=False
            )

        for filename in filenames:
            pathstr = joinpath(current_dirpath, filename)
            if filter_function and not filter_function(pathstr):
                continue
            statinfo = osstat(pathstr)
            _add_snapshot_db_entry(
                cursor, pathstr, statinfo, is_dir=False, is_file=True
            )
        if not walk:
            # don't continue walking the the tree
            break

    conn.commit()


def is_snapshot_file(pathstr: str) -> bool:
    """Return True if the given path is a snapshot database file, otherwise False"""
    pathstr = os.path.abspath(os.path.expanduser(pathstr))
    try:
        conn = sqlite3.connect(f"file:{pathstr}?mode=ro", uri=True)
        cursor = conn.cursor()
        return (
            cursor.execute(
                """
        SELECT count(*)
        FROM sqlite_master
        WHERE type='table'
        AND name='snapshot';
        """
            ).fetchone()[0]
            == 1
        )
    except Exception as e:
        return False


def _open_snapshot_db(
    dbpath: str, dirpath: Optional[str] = None, description: Optional[str] = None
) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    """Open a snapshot database, initializing if needed, and return a connection and cursor

    Args:
        dbpath: path to database to open
        dirpath: path to the directory to snapshot
        description: optional description of the snapshot

    Returns:
        sqlite3.Connection, sqlite3.Cursor
    """

    conn = sqlite3.connect(dbpath)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshot (
            path TEXT, 
            is_dir INTEGER,
            is_file INTEGER,
            st_mode INTEGER, 
            st_uid INTEGER, 
            st_gid INTEGER, 
            st_size INTEGER, 
            st_mtime INTEGER);
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS _metadata (
            description TEXT, source TEXT, version TEXT, created_at DATETIME);
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS about (
            description TEXT, directory TEXT, datetime DATETIME);
    """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS snapshot_path_index ON snapshot (path);
        """
    )

    now = datetime.datetime.now().isoformat()
    description = description or f"snapshot created by {__file__} at {now}"
    dirpath = dirpath or ""
    cursor.execute("INSERT INTO about VALUES (?, ?, ?)", (description, dirpath, now))
    cursor.execute(
        "INSERT INTO _metadata VALUES (?, ?, ?, ?)",
        (METADATA_DESCRIPTION, METADATA_SOURCE, __version__, now),
    )
    conn.commit()
    return conn, cursor


def _add_snapshot_db_entry(
    cursor: sqlite3.Cursor,
    pathstr: str,
    statinfo: os.stat_result,
    is_dir: bool,
    is_file: bool,
):
    cursor.execute(
        """INSERT INTO snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            pathstr,
            1 if is_dir else 0,
            1 if is_file else 0,
            statinfo.st_mode,
            statinfo.st_uid,
            statinfo.st_gid,
            statinfo.st_size,
            statinfo.st_mtime,
        ),
    )


class DirDiff:
    def __init__(
        self,
        snapshot_a: str,
        directory_or_snapshot_b: str,
        walk: bool = True,
        filter_function: Optional[Callable[[str], bool]] = None,
    ):
        """Initialize the DirDiff instance

        Args:
            snapshot_a: path to previous snapshot database to compare
            directory_or_snapshot_b: path to current snapshot database or path to directory to compare snapshot_a to
            walk: if True, walks the directory tree dir_b and recursively adds all files and directories

        Note: May be initialized with snapshot_a and dir_b to compare a current directory (dir_b) to previous snapshot (snapshot_a)
        or with snapshot_a and snapshot_b to compare older snapshot (snapshot_a) to newer snapshot (snapshot_b), but not both.
        """
        self.snapshot_a = snapshot_a
        if not is_snapshot_file(snapshot_a):
            raise ValueError(f"{snapshot_a} is not a snapshot database")

        if os.path.isdir(directory_or_snapshot_b):
            self.dir_b = directory_or_snapshot_b
            self.snapshot_b = None
        elif is_snapshot_file(directory_or_snapshot_b):
            self.dir_b = ""
            self.snapshot_b = directory_or_snapshot_b
        else:
            raise ValueError(
                f"{directory_or_snapshot_b} is not a directory or a snapshot database"
            )

        self._diff: Optional[DirDiffResults] = None
        self.walk = walk
        self.filter_function = filter_function

        self.snapshot_a_conn = sqlite3.connect(self.snapshot_a)
        self.snapshot_b_conn = (
            sqlite3.connect(self.snapshot_b)
            if self.snapshot_b
            else snapshot_memory(self.dir_b, walk=self.walk)
        )

    def diff(self) -> DirDiffResults:
        """Compare the current directory or snapshot to the previous snapshot

        Returns:
            diff results as DirDiffResults namedtuple
        """
        self._diff = self._diff_snapshots(
            self.snapshot_a_conn, self.snapshot_b_conn  # type: ignore
        )
        return self._diff

    def json(self, indent=2) -> str:
        """Return the diff results as JSON"""

        return json.dumps(self.diff()._asdict(), indent=indent)

    def report(self, include_identical=False) -> None:
        """Print a report of the diff to stdout.

        Args:
            include_identical: if True, print files that are identical
        """

        diff = self.diff()

        if self.dir_b:
            dirpath = self.dir_b
            dt_b = datetime.datetime.now().isoformat()
            about_b = f"snapshot created by {__file__} at {dt_b}"
            info_b = SnapshotInfo(description=about_b, directory=dirpath, datetime=dt_b)
            info_a = self.get_snapshot_info(self.snapshot_a_conn)  # type: ignore
        else:
            info_a = self.get_snapshot_info(self.snapshot_a_conn)  # type: ignore
            info_b = self.get_snapshot_info(self.snapshot_b_conn)  # type: ignore

        print(
            f"diff '{info_a.directory}' {info_a.datetime} ({info_a.description}) vs {info_b.datetime} ({info_b.description})"
        )
        print("Added: ")
        print("\n".join([f"    {f}" for f in diff.added]))
        if diff.added:
            print()
        print("Removed: ")
        print("\n".join([f"    {f}" for f in diff.removed]))
        if diff.removed:
            print()
        print("Modified: ")
        print("\n".join([f"    {f}" for f in diff.modified]))
        if diff.modified and include_identical:
            print()
        if include_identical:
            print("Identical: ")
            print("\n".join([f"    {f}" for f in diff.identical]))

    def get_snapshot_info(self, conn: sqlite3.Connection) -> SnapshotInfo:
        """Return info about a snapshot as a named tuple.

        Args:
            conn: sqlite3.Connection to the snapshot database

        Returns:
            (description string, path to directory, datetime string)
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT description, directory, datetime FROM about ORDER BY datetime DESC LIMIT 1"
        )
        description, directory, dt = cursor.fetchone()
        return SnapshotInfo(description, directory, dt)

    def _diff_snapshots(
        self, conn_a: sqlite3.Connection, conn_b: sqlite3.Connection
    ) -> DirDiffResults:
        """Diff two database snapshots

        Args:
            conn_a: Connection to snapshot a db (the previous snapshot)
            conn_b: Connection to snapshot b db (the current snapshot)

        Returns:
            DirDiffResults namedtuple
        """
        diffresults: Dict = {
            "added": [],
            "removed": [],
            "modified": [],
            "identical": [],
        }
        cursor_a = conn_a.cursor()
        cursor_b = conn_b.cursor()
        paths_b = {}
        for row in cursor_b.execute("SELECT * FROM snapshot"):
            pathstr, is_dir, is_file, st_mode, st_uid, st_gid, st_size, st_mtime = row
            if self.filter_function and not self.filter_function(pathstr):
                continue
            paths_b[pathstr] = 1
            cursor_a.execute("""SELECT * FROM snapshot WHERE path = ?""", (pathstr,))
            if row_b := cursor_a.fetchone():
                # TODO: make this a compare function that can be passed in
                if (
                    row_b[1] != is_dir
                    or row_b[2] != is_file
                    or row_b[3] != st_mode
                    or row_b[4] != st_uid
                    or row_b[5] != st_gid
                    or row_b[6] != st_size
                    or row_b[7] != st_mtime
                ):
                    diffresults["modified"].append(pathstr)
                else:
                    diffresults["identical"].append(pathstr)
            else:
                diffresults["added"].append(pathstr)
        for row in cursor_a.execute("SELECT path FROM SNAPSHOT"):
            if self.filter_function and not self.filter_function(row[0]):
                continue
            if row[0] not in paths_b:
                diffresults["removed"].append(row[0])

        return DirDiffResults(**diffresults)
