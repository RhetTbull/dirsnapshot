Module dirsnapshot
==================
dirsnapshot

Sub-modules
-----------
* dirsnapshot.dirsnapshot

Functions
---------

    
`create_snapshot(dirpath: str, snapshot_db: str, walk: bool = True, description: Optional[str] = None, filter_function: Optional[Callable[[str], bool]] = None) ‑> dirsnapshot.dirsnapshot.DirSnapshot`
:   Factory function to create a snapshot of a directory
    
    Args:
        dir: path to directory to snapshot
        snapshot_db: path to database to write snapshot to
        walk: if True, walk the directory tree and add all files and directories
        description: optional description of the snapshot
        filter: optional function to filter out files and directories; should return True if the file or directory should be included in the snapshot
    
    Returns:
        DirSnapshot object
    
    Raises:
        ValueError if snapshot_db already exists

    
`create_snapshot_in_memory(dirpath: str, walk: bool = True, description: Optional[str] = None, filter_function: Optional[Callable[[str], bool]] = None) ‑> dirsnapshot.dirsnapshot.DirSnapshot`
:   Factory function to create a snapshot of a directory in memory
    
    Args:
        dir: path to directory to snapshot
        walk: if True, walk the directory tree and add all files and directories
        description: optional description of the snapshot
    
    Returns:
        DirSnapshot object

    
`load_snapshot(snapshot_db: str) ‑> dirsnapshot.dirsnapshot.DirSnapshot`
:   Factory function to load a snapshot from a database file
    
    Args:
        snapshot_db: path to database file
    
    Returns:
        DirSnapshot object

Classes
-------

`DirDiff(snapshot_a: Union[str, dirsnapshot.dirsnapshot.DirSnapshot], directory_or_snapshot_b: Union[str, dirsnapshot.dirsnapshot.DirSnapshot], walk: bool = True, filter_function: Optional[Callable[[str], bool]] = None)`
:   Initialize the DirDiff instance
    
    Args:
        snapshot_a: path to previous snapshot database to compare or a DirSnapshot instance
        directory_or_snapshot_b: path to current snapshot database, DirSnapshot instance, or path to directory to compare snapshot_a to
        walk: if True, walks the directory tree and recursively adds all files and directories

    ### Methods

    `compare_records(self, record_a: dirsnapshot.dirsnapshot.SnapshotRecord, record_b: dirsnapshot.dirsnapshot.SnapshotRecord) ‑> bool`
    :   The default compare function for DirDiff.diff();
        override this in your subclass to implement custom compare, or use compare_function arg to diff
        
        Args:
            record_a: first SnapshotRecord to compare
            record_b: second SnapshotRecord to compare
        
        Returns:
            True if the records are equal, otherwise False

    `diff(self, compare_function: Optional[Callable[[dirsnapshot.dirsnapshot.SnapshotRecord, dirsnapshot.dirsnapshot.SnapshotRecord], bool]] = None) ‑> dirsnapshot.dirsnapshot.DirDiffResults`
    :   Compare the current directory or snapshot to the previous snapshot
        
        Args:
            `compare_function`: optional function to filter the results, receives a pair of SnapshotRecords and returns True if the pair are equal, otherwise False
        
        Returns:
            diff results as DirDiffResults instance

    `report(self, include_identical=False) ‑> None`
    :   Print a report of the diff to stdout.
        
        Args:
            include_identical: if True, print files that are identical

`DirDiffResults(added: List[str], removed: List[str], modified: List[str], identical: List[str])`
:   Results of a directory comparison as returned by DirDiff.diff()

    ### Class variables

    `added: List[str]`
    :

    `identical: List[str]`
    :

    `modified: List[str]`
    :

    `removed: List[str]`
    :

    ### Methods

    `asdict(self)`
    :

    `json(self)`
    :

`DirSnapshotis_snapshot_file(added: List[str], removed: List[str], modified: List[str], identical: List[str])`
:   Results of a directory comparison as returned by DirDiff.diff()

    ### Class variables

    `added: List[str]`
    :

    `identical: List[str]`
    :

    `modified: List[str]`
    :

    `removed: List[str]`
    :

    ### Methods

    `asdict(self)`
    :

    `json(self)`
    :

`SnapshotInfo(description, directory, datetime)`
:   SnapshotInfo(description, directory, datetime)

    ### Ancestors (in MRO)

    * builtins.tuple

    ### Instance variables

    `datetime`
    :   Alias for field number 2

    `description`
    :   Alias for field number 0

    `directory`
    :   Alias for field number 1

`SnapshotRecord(path: str, is_dir: bool, is_file: bool, mode: int, uid: int, gid: int, size: int, mtime: int, user_data: Optional[Any] = None)`
:   Snapshot details for a file or directory.
    
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

    ### Class variables

    `gid: int`
    :

    `is_dir: bool`
    :

    `is_file: bool`
    :

    `mode: int`
    :

    `mtime: int`
    :

    `path: str`
    :

    `size: int`
    :

    `uid: int`
    :

    `user_data: Optional[Any]`
    :

    ### Methods

    `asdict(self)`
    :