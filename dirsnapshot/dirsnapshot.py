"""Report differences between a directory and a previous snapshot of the same directory. 

This works very similar to [dircmp](https://docs.python.org/3/library/filecmp.html#the-dircmp-class) 
but it is designed to be used with a directory that is being monitored instead of comparing two 
existing directories.

This module can be run as a standalone CLI app or included in your project as a module.
"""

import dataclasses
import datetime
import json
import os
import sqlite3
from collections import namedtuple
from dataclasses import dataclass
from os import stat as osstat
from os import walk as oswalk
from os.path import exists as pathexists
from os.path import join as joinpath
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

from ._version import __version__

# Note: os.stat, os.walk, os.path.exists, os.path.join are imported as separate names
# because this increases performance slightly and these will be called repeatedly to
# create the snapshot


__all__ = [
    "create_snapshot",
    "DirDiff",
    "DirDiffResults",
    "DirSnapshot" "is_snapshot_file",
    "load_snapshot",
    "SnapshotInfo",
    "SnapshotRecord",
]

METADATA_SOURCE = "https://github.com/RhetTbull/dirsnapshot"
METADATA_DESCRIPTION = "Directory Snapshot created by dirsnapshot"


"""Info about a snapshot returned by DirSnapshot.info"""
SnapshotInfo = namedtuple("SnapshotInfo", ["description", "directory", "datetime"])


def create_snapshot(
    dirpath: str,
    snapshot_db: Optional[str],
    walk: bool = True,
    description: Optional[str] = None,
    filter_function: Optional[Callable[[str], bool]] = None,
) -> "DirSnapshot":
    """Factory function to create a snapshot of a directory

    Args:
        dir: path to directory to snapshot
        snapshot_db: path to database to write snapshot to or None to create database in memory
        walk: if True, walk the directory tree and add all files and directories
        description: optional description of the snapshot
        filter: optional function to filter out files and directories; should return True if the file or directory should be included in the snapshot

    Returns:
        DirSnapshot object

    Raises:
        ValueError if snapshot_db already exists
    """

    snapshot_db = snapshot_db or ":memory:"
    if snapshot_db != ":memory:" and pathexists(snapshot_db):
        raise ValueError(f"Snapshot database {snapshot_db} already exists")

    snapshot = DirSnapshot()
    snapshot.init_from_dir(dirpath, snapshot_db, walk, description, filter_function)
    return snapshot


def load_snapshot(snapshot_db: str) -> "DirSnapshot":
    """Factory function to load a snapshot from a database file

    Args:
        snapshot_db: path to database file

    Returns:
        DirSnapshot object
    """
    snapshot = DirSnapshot()
    snapshot.load_from_snapshot_db(snapshot_db)
    return snapshot


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


@dataclass
class SnapshotRecord:
    """Snapshot details for a file or directory.

    Attributes:
        path: path to file or directory
        is_dir: True if the path is a directory, False if it is a file
        is_file: True if the path is a file, False if it is a directory
        mode: file mode of file or directory
        uid: user ID of file or directory
        gid: group ID of file or directory
        size: size of file or directory in bytes
        mtime: modification time of file or directory
        user_data: optional user data associated with the file or directory
    """

    path: str
    is_dir: bool
    is_file: bool
    mode: int
    uid: int
    gid: int
    size: int
    mtime: int
    user_data: Optional[Any] = None

    def asdict(self):
        """Return a dict representation of the snapshot record"""
        return dataclasses.asdict(self)


class DirSnapshot:
    """Create a snapshot of a directory for use with DirDiff"""

    def __init__(self):
        pass

    def init_from_dir(
        self,
        dirpath: str,
        snapshot_db: str,
        walk: bool = True,
        description: Optional[str] = None,
        filter_function: Optional[Callable[[str], bool]] = None,
    ):
        """Create a snapshot from a directory

        Args:
            dirpath: path to the directory to snapshot
            snapshot_db: path to database to write snapshot to
            walk: if True, walk the directory tree and add all files and directories
            description: optional description of the snapshot
            filter: optional function to filter out files and directories; should return True if the file or directory should be included in the snapshot
        """
        if pathexists(snapshot_db):
            raise ValueError(f"Snapshot database {snapshot_db} already exists")
        if not os.path.isdir(dirpath):
            raise ValueError(
                f"Directory {dirpath} does not exist or is not a directory"
            )

        conn, cursor = self._create_snapshot_db(snapshot_db, dirpath, description)
        self.conn = conn
        self._snapshot(dirpath, walk, conn, cursor, filter_function)

    def load_from_snapshot_db(self, snapshot_db: str):
        """Load a snapshot from a database file

        Args:
            snapshot_db: path to database file
        """
        if not is_snapshot_file(snapshot_db):
            raise ValueError(f"{snapshot_db} is not a snapshot database")
        conn, _ = self._open_snapshot_db(snapshot_db)
        self.conn = conn

    @property
    def description(self) -> str:
        """Return the description of the snapshot"""
        return self.info.description

    @property
    def directory(self) -> str:
        """Return the directory of the snapshot"""
        return self.info.directory

    @property
    def datetime(self) -> datetime.datetime:
        """Return the datetime of the snapshot"""
        return datetime.datetime.fromisoformat(self.info.datetime)

    @property
    def info(self) -> SnapshotInfo:
        """Return info about a snapshot as a named tuple.

        Returns:
            SnapshotInfo named tuple
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT description, directory, datetime FROM about ORDER BY datetime DESC LIMIT 1"
        )
        description, directory, dt = cursor.fetchone()
        return SnapshotInfo(description, directory, dt)

    def files(self) -> Iterator[str]:
        """Generator to return all files in the snapshot"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT path FROM snapshot")
        for row in cursor:
            yield row[0]

    def record(self, filepath: str) -> Optional[SnapshotRecord]:
        """Return the snapshot record for a filepath or None if the filepath is not in the snapshot"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT path, is_dir, is_file, st_mode, st_uid, st_gid, st_size, st_mtime, user_data FROM snapshot WHERE path = ?",
            (filepath,),
        )
        results = cursor.fetchone()
        if results is None:
            return None
        return SnapshotRecord(*results)

    def records(self) -> Iterator[SnapshotRecord]:
        """Generator to return all files in the snapshot"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT path, is_dir, is_file, st_mode, st_uid, st_gid, st_size, st_mtime FROM snapshot"
        )
        for row in cursor:
            yield SnapshotRecord(*row)

    def _create_snapshot_db(
        self,
        dbpath: str,
        dirpath: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Initialize a snapshot db, and return a connection and cursor

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
                st_mtime INTEGER,
                user_data BLOB
                );
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
        description = description or f"Snapshot created at {now}"
        dirpath = dirpath or ""
        cursor.execute(
            "INSERT INTO about VALUES (?, ?, ?)", (description, dirpath, now)
        )
        cursor.execute(
            "INSERT INTO _metadata VALUES (?, ?, ?, ?)",
            (METADATA_DESCRIPTION, METADATA_SOURCE, __version__, now),
        )
        conn.commit()
        return conn, cursor

    def _open_snapshot_db(
        self, dbpath: str
    ) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Open a snapshot db, and return a connection and cursor

        Args:
            dbpath: path to database to open

        Returns:
            sqlite3.Connection, sqlite3.Cursor
        """
        conn = sqlite3.connect(dbpath)
        cursor = conn.cursor()
        return conn, cursor

    def _add_snapshot_db_entry(
        self,
        cursor: sqlite3.Cursor,
        pathstr: str,
        statinfo: os.stat_result,
        is_dir: bool,
        is_file: bool,
    ):
        cursor.execute(
            """INSERT INTO snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pathstr,
                1 if is_dir else 0,
                1 if is_file else 0,
                statinfo.st_mode,
                statinfo.st_uid,
                statinfo.st_gid,
                statinfo.st_size,
                statinfo.st_mtime,
                b"",
            ),
        )

    def _snapshot(
        self,
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
                self._add_snapshot_db_entry(
                    cursor, pathstr, statinfo, is_dir=True, is_file=False
                )

            for filename in filenames:
                pathstr = joinpath(current_dirpath, filename)
                if filter_function and not filter_function(pathstr):
                    continue
                statinfo = osstat(pathstr)
                self._add_snapshot_db_entry(
                    cursor, pathstr, statinfo, is_dir=False, is_file=True
                )
            if not walk:
                # don't continue walking the the tree
                break

        conn.commit()


@dataclass
class DirDiffResults:
    """Results of a directory comparison as returned by DirDiff.diff()"""

    added: List[str]
    removed: List[str]
    modified: List[str]
    identical: List[str]

    def asdict(self):
        return dataclasses.asdict(self)

    def json(self):
        return json.dumps(self.asdict())


class DirDiff:
    def __init__(
        self,
        snapshot_a: Union[str, DirSnapshot],
        directory_or_snapshot_b: Union[str, DirSnapshot],
        walk: bool = True,
        filter_function: Optional[Callable[[str], bool]] = None,
    ):
        """Initialize the DirDiff instance

        Args:
            snapshot_a: path to previous snapshot database to compare or a DirSnapshot instance
            directory_or_snapshot_b: path to current snapshot database, DirSnapshot instance, or path to directory to compare snapshot_a to
            walk: if True, walks the directory tree and recursively adds all files and directories
        """

        if isinstance(snapshot_a, str):
            self.snapshot_a = load_snapshot(snapshot_a)
        elif isinstance(snapshot_a, DirSnapshot):
            self.snapshot_a = snapshot_a
        else:
            raise ValueError(
                f"{snapshot_a} is not a snapshot database or DirSnapshot instance"
            )

        if isinstance(directory_or_snapshot_b, DirSnapshot):
            self.snapshot_b = directory_or_snapshot_b
        elif os.path.isdir(directory_or_snapshot_b):
            self.snapshot_b = create_snapshot(directory_or_snapshot_b, None, walk)
        elif is_snapshot_file(directory_or_snapshot_b):
            self.snapshot_b = load_snapshot(directory_or_snapshot_b)
        else:
            raise ValueError(
                f"{directory_or_snapshot_b} is not a directory or a snapshot database"
            )

        self._diff: Optional[DirDiffResults] = None
        self.walk = walk
        self.filter_function = filter_function

    def diff(
        self,
        compare_function: Optional[
            Callable[[SnapshotRecord, SnapshotRecord], bool]
        ] = None,
    ) -> DirDiffResults:
        """Compare the current directory or snapshot to the previous snapshot

        Args:
            `compare_function`: optional function to filter the results, receives a pair of SnapshotRecords and returns True if the pair are equal, otherwise False

        Returns:
            diff results as DirDiffResults instance
        """
        self._diff = self._diff_snapshots(compare_function)
        return self._diff

    def report(self, include_identical=False) -> None:
        """Print a report of the diff to stdout.

        Args:
            include_identical: if True, print files that are identical
        """

        diff = self.diff()

        info_a = self.snapshot_a.info
        info_b = self.snapshot_b.info
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

    def compare_records(
        self, record_a: SnapshotRecord, record_b: SnapshotRecord
    ) -> bool:
        """The default compare function for DirDiff.diff();
        override this in your subclass to implement custom compare, or use compare_function arg to diff

        Args:
            record_a: first SnapshotRecord to compare
            record_b: second SnapshotRecord to compare

        Returns:
            True if the records are equal, otherwise False
        """
        return (
            record_a.is_dir == record_b.is_dir
            and record_a.is_file == record_b.is_file
            and record_a.mode == record_b.mode
            and record_a.uid == record_b.uid
            and record_a.gid == record_b.gid
            and record_a.size == record_b.size
            and record_a.mtime == record_b.mtime
        )

    def _diff_snapshots(
        self,
        compare_function: Optional[
            Callable[[SnapshotRecord, SnapshotRecord], bool]
        ] = None,
    ) -> DirDiffResults:
        """Diff two database snapshots

        Returns:
            DirDiffResults instance
        """
        diffresults: Dict = {
            "added": [],
            "removed": [],
            "modified": [],
            "identical": [],
        }

        compare_function = compare_function or self.compare_records

        paths_b = {}
        for row_b in self.snapshot_b.records():
            if self.filter_function and not self.filter_function(row_b.path):
                continue
            paths_b[row_b.path] = 1
            if row_a := self.snapshot_a.record(row_b.path):
                if not compare_function(row_a, row_b):
                    diffresults["modified"].append(row_b.path)
                else:
                    diffresults["identical"].append(row_b.path)
            else:
                diffresults["added"].append(row_b.path)
        for row_a in self.snapshot_a.records():
            if self.filter_function and not self.filter_function(row_a.path):
                continue
            if row_a.path not in paths_b:
                diffresults["removed"].append(row_a.path)

        return DirDiffResults(**diffresults)
