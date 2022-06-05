import argparse
import os.path
import re

from .dirsnapshot import DirDiff, DirDiffResults, is_snapshot_file, snapshot


def cli():
    """
    Compare a directory to a previously saved snapshot or compare two directory snapshots.

    You must specify one of --snapshot or --diff.

    Will show files added/removed/modified.

    Files are considered modified if any of mode, uid, gid, size, or mtime are different.
    """
    from textwrap import dedent

    parser = argparse.ArgumentParser(description=dedent(cli.__doc__))
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--snapshot",
        "-s",
        nargs=2,
        metavar=("DIRECTORY", "SNAPSHOT_FILE"),
        help="Create snapshot of DIRECTORY at SNAPSHOT_FILE",
    )
    parser.add_argument(
        "--diff",
        nargs=2,
        metavar=("SNAPSHOT_A", "DIRECTORY_OR_SNAPSHOT_B"),
        help="Diff SNAPSHOT_A and DIRECTORY_OR_SNAPSHOT_B",
    )
    parser.add_argument(
        "--descr",
        "-d",
        nargs=1,
        metavar="DESCRIPTION",
        help="Optional description of snapshot to store with snapshot for use with --snapshot.",
    )
    parser.add_argument(
        "--identical",
        "-I",
        action="store_true",
        help="Include identical files in report (always included with --json)",
    )
    parser.add_argument(
        "--ignore",
        "-i",
        action="append",
        metavar="REGEX",
        help="Ignore files matching REGEX",
    )
    parser.add_argument("--no-walk", action="store_true", help="Don't walk directories")
    args = parser.parse_args()

    # validate args
    if args.snapshot and args.diff:
        parser.error("--snapshot and --diff are mutually exclusive")

    if not (args.snapshot or args.diff):
        parser.error("You must specify one of --snapshot or --diff")

    if args.descr and not args.snapshot:
        parser.error("--descr can only be used with --snapshot")

    if (args.json or args.identical) and not args.diff:
        parser.error("--json and --identical can only be used with --diff")

    if args.ignore:

        def ignore_func(path: str) -> bool:
            return not any(re.search(pattern, path) for pattern in args.ignore)

    else:
        ignore_func = None

    if args.snapshot:
        snapshot_dir, snapshot_file = args.snapshot
        if os.path.exists(snapshot_file):
            parser.error(f"{snapshot_file} already exists")
        if not os.path.isdir(snapshot_dir):
            parser.error(f"{snapshot_dir} is not a directory")
        about = args.descr[0] if args.descr else None
        print(f"Creating snapshot of '{snapshot_dir}' at '{snapshot_file}'")
        snapshot(
            snapshot_dir,
            snapshot_file,
            walk=not args.no_walk,
            description=about,
            filter_function=ignore_func,
        )
        print(f"Snapshot created at '{snapshot_file}'")

    if args.diff:
        snapshot_a, snapshot_b = args.diff
        if not os.path.exists(snapshot_a):
            parser.error(f"{snapshot_a} does not exist")
        if not os.path.exists(snapshot_b):
            parser.error(f"{snapshot_b} does not exist")

        if os.path.isdir(snapshot_b) and os.path.isfile(snapshot_a):
            if not is_snapshot_file(snapshot_a):
                parser.error(f"{snapshot_a} is not a snapshot file")
            dirdiff = DirDiff(
                snapshot_a=snapshot_a,
                dir_b=snapshot_b,
                walk=not args.no_walk,
                filter_function=ignore_func,
            )
        elif os.path.isfile(snapshot_a) and os.path.isfile(snapshot_b):
            for f in [snapshot_a, snapshot_b]:
                if not is_snapshot_file(f):
                    parser.error(f"{f} is not a snapshot file")
            dirdiff = DirDiff(
                snapshot_a=snapshot_a,
                snapshot_b=snapshot_b,
                filter_function=ignore_func,
            )
        else:
            parser.error(
                "snapshots must either be directory + snapshot file or two snapshot files"
            )
        if args.json:
            print(dirdiff.json())
        else:
            dirdiff.report(include_identical=args.identical)


if __name__ == "__main__":
    cli()
