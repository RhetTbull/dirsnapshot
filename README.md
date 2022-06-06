# dirsnapshot

## Description

Report differences between a directory and a previous snapshot of the same directory.

This works very similar to [dircmp](https://docs.python.org/3/library/filecmp.html#the-dircmp-class) but it is designed to be used with a directory that is being monitored instead of comparing two existing directories.

This module can be run as a standalone CLI app as `dirsnap` or included in your project as a package.

## Usage

```python
from dirsnapshot import DirDiff, snapshot

# snapshot a directory
create_snapshot("/Users/user/Desktop", "/Users/user/Desktop/Desktop.snapshot")

# do some work
...

# compare the current state of the director to the snapshot
dirdiff = DirDiff("/Users/user/Desktop/Desktop.snapshot", "/Users/user/Desktop")

# print report to stdout
dirdiff.report()

# or print report to json
print(dirdiff.json())
```

## Installation

```bash
pip install dirsnapshot
```

## CLI

Installing the `dirsnapshot` package will install a command line tool called `dirsnap` that can be used to create snapshots of directories and compare a directory to an existing snapshot.

```
usage: dirsnap [-h] [--json] [--snapshot DIRECTORY SNAPSHOT_FILE]
               [--diff SNAPSHOT_A DIRECTORY_OR_SNAPSHOT_B]
               [--descr DESCRIPTION] [--identical] [--ignore REGEX]
               [--no-walk]

Compare a directory to a previously saved snapshot or compare two directory
snapshots. You must specify one of --snapshot or --diff. Will show files
added/removed/modified. Files are considered modified if any of mode, uid,
gid, size, or mtime are different.

options:
  -h, --help            show this help message and exit
  --json, -j            Output as JSON
  --snapshot DIRECTORY SNAPSHOT_FILE, -s DIRECTORY SNAPSHOT_FILE
                        Create snapshot of DIRECTORY at SNAPSHOT_FILE
  --diff SNAPSHOT_A DIRECTORY_OR_SNAPSHOT_B
                        Diff SNAPSHOT_A and DIRECTORY_OR_SNAPSHOT_B
  --descr DESCRIPTION, -d DESCRIPTION
                        Optional description of snapshot to store with
                        snapshot for use with --snapshot.
  --identical, -I       Include identical files in report (always included
                        with --json)
  --ignore REGEX, -i REGEX
                        Ignore files matching REGEX
  --no-walk             Don't walk directories
```

For example:

```bash
$ dirsnap --snapshot ~/Desktop/export before.snapshot
Creating snapshot of '/Users/username/Desktop/export' at 'before.snapshot'
Snapshot created at 'before.snapshot'

$ touch ~/Desktop/export/IMG_4548.jpg
$ rm ~/Desktop/export/IMG_4547.jpg
$ touch ~/Desktop/export/new_file.jpg

$ dirsnap --diff before.snapshot ~/Desktop/export
diff '/Users/username/Desktop/export' 2022-06-05T18:38:11.189886 (Snapshot created at 2022-06-05T18:38:11.189886) vs 2022-06-05T18:39:07.225374 (Snapshot created at 2022-06-05T18:39:07.225374)

Added:
    /Users/username/Desktop/export/new_file.jpg

Removed:
    /Users/username/Desktop/export/IMG_4547.jpg

Modified:
    /Users/username/Desktop/export/IMG_4548.jpg
```


