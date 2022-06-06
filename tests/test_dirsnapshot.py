"""Test dirsnapshot """

import json
import pathlib
from typing import List
import datetime

import pytest

from dirsnapshot import (
    DirDiff,
    DirDiffResults,
    DirSnapshot,
    SnapshotInfo,
    SnapshotRecord,
    __version__,
    create_snapshot,
    load_snapshot,
    is_snapshot_file,
)


def populate_dir(dirpath: pathlib.Path) -> List[str]:
    """Populate test directory with files"""
    files = []
    for i in range(10):
        with open(dirpath / f"file_{i}", "w") as f:
            f.write(f"file_{i}")
            files.append(dirpath / f.name)

    for i in range(2):
        subdir = dirpath / f"dir_{i}"
        subdir.mkdir()
        files.append(subdir)
        for j in range(10):
            with open(subdir / f"file_{i}_{j}", "w") as f:
                f.write(f"file_{i}_{j}")
                files.append(subdir / f.name)

    return [str(f) for f in files]


def test_version():
    """Test version"""
    assert __version__ == "0.1.0"


def test_is_snapshot_file(tmp_path: pathlib.Path):
    """Test is_snapshot_file"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    snapshot_file = tmp_path / f"{d1}.snapshot"

    populate_dir(d1)
    create_snapshot(str(d1), str(snapshot_file))
    assert is_snapshot_file(snapshot_file)

    snapshot_file = tmp_path / "not_a_snapshot"
    snapshot_file.touch()
    assert not is_snapshot_file(snapshot_file)


def test_dirdiff_two_snapshots(tmp_path: pathlib.Path, capsys):
    """Test DirDiff with two snapshots"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    snapshot_1 = create_snapshot(str(d1), str(snapshot_file1), description="snapshot-1")
    assert snapshot_1.description == "snapshot-1"

    # remove a file
    (d1 / "file_0").unlink()

    # add a file
    (d1 / "file_10").touch()

    # modify a file
    (d1 / "file_1").write_text("modified")

    # modify a file in a subdirectory
    (d1 / "dir_0" / "file_0_0").write_text("modified")

    # remove a file in a subdirectory
    (d1 / "dir_1" / "file_1_0").unlink()

    # add a file in a subdirectory
    (d1 / "dir_0" / "file_0_10").touch()

    # snapshot 2
    snapshot_file2 = tmp_path / "2.snapshot"
    snapshot_2 = create_snapshot(str(d1), str(snapshot_file2), description="snapshot-2")
    assert snapshot_2.description == "snapshot-2"

    dirdiff = DirDiff(
        str(snapshot_file1),
        str(snapshot_file2),
    )
    diff = dirdiff.diff()
    assert isinstance(diff, DirDiffResults)
    assert sorted(diff.removed) == sorted(
        [str(f) for f in [d1 / "file_0", d1 / "dir_1" / "file_1_0"]]
    )
    assert sorted(diff.added) == sorted(
        [str(f) for f in [d1 / "file_10", d1 / "dir_0" / "file_0_10"]]
    )
    assert sorted(diff.modified) == sorted(
        [
            str(f)
            for f in [
                d1 / "file_1",
                d1 / "dir_0" / "file_0_0",
                d1 / "dir_0",
                d1 / "dir_1",
            ]
        ]
    )

    # remove files we changed/added/removed from files list for comparing identical
    files.remove(str(d1 / "dir_0"))
    files.remove(str(d1 / "dir_1"))
    files.remove(str(d1 / "file_0"))
    files.remove(str(d1 / "file_1"))
    files.remove(str(d1 / "dir_0" / "file_0_0"))
    files.remove(str(d1 / "dir_1" / "file_1_0"))

    assert sorted(diff.identical) == sorted(files)

    # test json
    json_dict = json.loads(dirdiff.json())
    assert sorted(json_dict["added"]) == sorted(diff.added)
    assert sorted(json_dict["removed"]) == sorted(diff.removed)
    assert sorted(json_dict["modified"]) == sorted(diff.modified)
    assert sorted(json_dict["identical"]) == sorted(diff.identical)

    # test description
    dirdiff.report()
    output = capsys.readouterr().out.strip()
    assert "(snapshot-1)" in output
    assert "(snapshot-2)" in output


def test_dirdiff_two_snapshot_objects(tmp_path: pathlib.Path, capsys):
    """Test DirDiff with two snapshot objects"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    snapshot_1 = create_snapshot(str(d1), str(snapshot_file1), description="snapshot-1")
    assert snapshot_1.description == "snapshot-1"

    # remove a file
    (d1 / "file_0").unlink()

    # add a file
    (d1 / "file_10").touch()

    # modify a file
    (d1 / "file_1").write_text("modified")

    # modify a file in a subdirectory
    (d1 / "dir_0" / "file_0_0").write_text("modified")

    # remove a file in a subdirectory
    (d1 / "dir_1" / "file_1_0").unlink()

    # add a file in a subdirectory
    (d1 / "dir_0" / "file_0_10").touch()

    # snapshot 2
    snapshot_file2 = tmp_path / "2.snapshot"
    snapshot_2 = create_snapshot(str(d1), str(snapshot_file2), description="snapshot-2")
    assert snapshot_2.description == "snapshot-2"

    dirdiff = DirDiff(snapshot_1, snapshot_2)
    diff = dirdiff.diff()
    assert isinstance(diff, DirDiffResults)
    assert sorted(diff.removed) == sorted(
        [str(f) for f in [d1 / "file_0", d1 / "dir_1" / "file_1_0"]]
    )
    assert sorted(diff.added) == sorted(
        [str(f) for f in [d1 / "file_10", d1 / "dir_0" / "file_0_10"]]
    )
    assert sorted(diff.modified) == sorted(
        [
            str(f)
            for f in [
                d1 / "file_1",
                d1 / "dir_0" / "file_0_0",
                d1 / "dir_0",
                d1 / "dir_1",
            ]
        ]
    )

    # remove files we changed/added/removed from files list for comparing identical
    files.remove(str(d1 / "dir_0"))
    files.remove(str(d1 / "dir_1"))
    files.remove(str(d1 / "file_0"))
    files.remove(str(d1 / "file_1"))
    files.remove(str(d1 / "dir_0" / "file_0_0"))
    files.remove(str(d1 / "dir_1" / "file_1_0"))

    assert sorted(diff.identical) == sorted(files)

    # test json
    json_dict = json.loads(dirdiff.json())
    assert sorted(json_dict["added"]) == sorted(diff.added)
    assert sorted(json_dict["removed"]) == sorted(diff.removed)
    assert sorted(json_dict["modified"]) == sorted(diff.modified)
    assert sorted(json_dict["identical"]) == sorted(diff.identical)

    # test description
    dirdiff.report()
    output = capsys.readouterr().out.strip()
    assert "(snapshot-1)" in output
    assert "(snapshot-2)" in output


def test_dirdiff_snapshot_dir(tmp_path: pathlib.Path):
    """Test DirDiff with snapshot and directory"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    create_snapshot(str(d1), str(snapshot_file1), description="snapshot-1")

    # remove a file
    (d1 / "file_0").unlink()

    # add a file
    (d1 / "file_10").touch()

    # modify a file
    (d1 / "file_1").write_text("modified")

    # modify a file in a subdirectory
    (d1 / "dir_0" / "file_0_0").write_text("modified")

    # remove a file in a subdirectory
    (d1 / "dir_1" / "file_1_0").unlink()

    # add a file in a subdirectory
    (d1 / "dir_0" / "file_0_10").touch()

    dirdiff = DirDiff(
        str(snapshot_file1),
        str(d1),
    )
    diff = dirdiff.diff()
    assert isinstance(diff, DirDiffResults)
    assert sorted(diff.removed) == sorted(
        [str(f) for f in [d1 / "file_0", d1 / "dir_1" / "file_1_0"]]
    )
    assert sorted(diff.added) == sorted(
        [str(f) for f in [d1 / "file_10", d1 / "dir_0" / "file_0_10"]]
    )
    assert sorted(diff.modified) == sorted(
        [
            str(f)
            for f in [
                d1 / "file_1",
                d1 / "dir_0" / "file_0_0",
                d1 / "dir_0",
                d1 / "dir_1",
            ]
        ]
    )

    # remove files we changed/added/removed from files list for comparing identical
    files.remove(str(d1 / "dir_0"))
    files.remove(str(d1 / "dir_1"))
    files.remove(str(d1 / "file_0"))
    files.remove(str(d1 / "file_1"))
    files.remove(str(d1 / "dir_0" / "file_0_0"))
    files.remove(str(d1 / "dir_1" / "file_1_0"))

    assert sorted(diff.identical) == sorted(files)


def test_dirdiff_filter_function_two_snapshots(tmp_path: pathlib.Path):
    """Test DirDiff with filter function and two snapshots"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    create_snapshot(str(d1), str(snapshot_file1))

    # remove a file
    (d1 / "file_0").unlink()

    # add a file
    (d1 / "file_10").touch()

    # modify a file
    (d1 / "file_1").write_text("modified")

    # modify a file in a subdirectory
    (d1 / "dir_0" / "file_0_0").write_text("modified")

    # remove a file in a subdirectory
    (d1 / "dir_1" / "file_1_0").unlink()

    # add a file in a subdirectory
    (d1 / "dir_0" / "file_0_10").touch()

    # snapshot 2
    snapshot_file2 = tmp_path / "2.snapshot"
    create_snapshot(str(d1), str(snapshot_file2))

    def filter_function(path):
        path = pathlib.Path(path)
        if path.name == "file_1":
            return False
        return True

    dirdiff = DirDiff(
        str(snapshot_file1),
        str(snapshot_file2),
        filter_function=filter_function,
    )
    diff = dirdiff.diff()
    assert isinstance(diff, DirDiffResults)
    assert sorted(diff.removed) == sorted(
        [str(f) for f in [d1 / "file_0", d1 / "dir_1" / "file_1_0"]]
    )
    assert sorted(diff.added) == sorted(
        [str(f) for f in [d1 / "file_10", d1 / "dir_0" / "file_0_10"]]
    )
    assert sorted(diff.modified) == sorted(
        [
            str(f)
            for f in [
                d1 / "dir_0" / "file_0_0",
                d1 / "dir_0",
                d1 / "dir_1",
            ]
        ]
    )

    # remove files we changed/added/removed from files list for comparing identical
    files.remove(str(d1 / "dir_0"))
    files.remove(str(d1 / "dir_1"))
    files.remove(str(d1 / "file_0"))
    files.remove(str(d1 / "dir_0" / "file_0_0"))
    files.remove(str(d1 / "file_1"))
    files.remove(str(d1 / "dir_1" / "file_1_0"))

    assert sorted(diff.identical) == sorted(files)


def test_dirdiff_filter_function_snapshot_dir(tmp_path: pathlib.Path):
    """Test DirDiff with filter function and snapshot and directory"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    create_snapshot(str(d1), str(snapshot_file1))

    # remove a file
    (d1 / "file_0").unlink()

    # add a file
    (d1 / "file_10").touch()

    # modify a file
    (d1 / "file_1").write_text("modified")

    # modify a file in a subdirectory
    (d1 / "dir_0" / "file_0_0").write_text("modified")

    # remove a file in a subdirectory
    (d1 / "dir_1" / "file_1_0").unlink()

    # add a file in a subdirectory
    (d1 / "dir_0" / "file_0_10").touch()

    def filter_function(path):
        path = pathlib.Path(path)
        if path.name == "file_1":
            return False
        return True

    dirdiff = DirDiff(
        str(snapshot_file1),
        str(d1),
        filter_function=filter_function,
    )
    diff = dirdiff.diff()
    assert isinstance(diff, DirDiffResults)
    assert sorted(diff.removed) == sorted(
        [str(f) for f in [d1 / "file_0", d1 / "dir_1" / "file_1_0"]]
    )
    assert sorted(diff.added) == sorted(
        [str(f) for f in [d1 / "file_10", d1 / "dir_0" / "file_0_10"]]
    )
    assert sorted(diff.modified) == sorted(
        [
            str(f)
            for f in [
                d1 / "dir_0" / "file_0_0",
                d1 / "dir_0",
                d1 / "dir_1",
            ]
        ]
    )

    # remove files we changed/added/removed from files list for comparing identical
    files.remove(str(d1 / "dir_0"))
    files.remove(str(d1 / "dir_1"))
    files.remove(str(d1 / "file_0"))
    files.remove(str(d1 / "dir_0" / "file_0_0"))
    files.remove(str(d1 / "file_1"))
    files.remove(str(d1 / "dir_1" / "file_1_0"))

    assert sorted(diff.identical) == sorted(files)


def test_snapshot_filter_function(tmp_path: pathlib.Path):
    """Test snapshot with filter function"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    def filter_function(path):
        path = pathlib.Path(path)
        if path.name == "file_1":
            return False
        return True

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    create_snapshot(str(d1), str(snapshot_file1), filter_function=filter_function)

    # remove a file
    (d1 / "file_0").unlink()

    # add a file
    (d1 / "file_10").touch()

    # modify a file
    (d1 / "file_1").write_text("modified")

    # modify a file in a subdirectory
    (d1 / "dir_0" / "file_0_0").write_text("modified")

    # remove a file in a subdirectory
    (d1 / "dir_1" / "file_1_0").unlink()

    # add a file in a subdirectory
    (d1 / "dir_0" / "file_0_10").touch()

    # snapshot 2
    snapshot_file2 = tmp_path / "2.snapshot"
    create_snapshot(str(d1), str(snapshot_file2), filter_function=filter_function)

    dirdiff = DirDiff(
        str(snapshot_file1),
        str(snapshot_file2),
    )
    diff = dirdiff.diff()
    assert isinstance(diff, DirDiffResults)
    assert sorted(diff.removed) == sorted(
        [str(f) for f in [d1 / "file_0", d1 / "dir_1" / "file_1_0"]]
    )
    assert sorted(diff.added) == sorted(
        [str(f) for f in [d1 / "file_10", d1 / "dir_0" / "file_0_10"]]
    )
    assert sorted(diff.modified) == sorted(
        [
            str(f)
            for f in [
                d1 / "dir_0" / "file_0_0",
                d1 / "dir_0",
                d1 / "dir_1",
            ]
        ]
    )

    # remove files we changed/added/removed from files list for comparing identical
    files.remove(str(d1 / "dir_0"))
    files.remove(str(d1 / "dir_1"))
    files.remove(str(d1 / "file_0"))
    files.remove(str(d1 / "dir_0" / "file_0_0"))
    files.remove(str(d1 / "file_1"))
    files.remove(str(d1 / "dir_1" / "file_1_0"))

    assert sorted(diff.identical) == sorted(files)


def test_snapshot_no_walk(tmp_path: pathlib.Path):
    """Test snapshot with walk=False"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    create_snapshot(str(d1), str(snapshot_file1), walk=False)

    # remove a file
    (d1 / "file_0").unlink()

    # add a file
    (d1 / "file_10").touch()

    # modify a file
    (d1 / "file_1").write_text("modified")

    # modify a file in a subdirectory
    (d1 / "dir_0" / "file_0_0").write_text("modified")

    # remove a file in a subdirectory
    (d1 / "dir_1" / "file_1_0").unlink()

    # add a file in a subdirectory
    (d1 / "dir_0" / "file_0_10").touch()

    # snapshot 2
    snapshot_file2 = tmp_path / "2.snapshot"
    create_snapshot(str(d1), str(snapshot_file2), walk=False)

    dirdiff = DirDiff(
        str(snapshot_file1),
        str(snapshot_file2),
    )
    diff = dirdiff.diff()
    assert isinstance(diff, DirDiffResults)
    assert sorted(diff.removed) == sorted([str(f) for f in [d1 / "file_0"]])
    assert sorted(diff.added) == sorted([str(f) for f in [d1 / "file_10"]])
    assert sorted(diff.modified) == sorted(
        [str(f) for f in [d1 / "file_1", d1 / "dir_0", d1 / "dir_1"]]
    )

    # remove files we changed/added/removed from files list for comparing identical
    files.remove(str(d1 / "dir_0"))
    files.remove(str(d1 / "dir_1"))
    files.remove(str(d1 / "file_0"))
    files.remove(str(d1 / "file_1"))
    files = [f for f in files if pathlib.Path(f).parent != d1 / "dir_0"]
    files = [f for f in files if pathlib.Path(f).parent != d1 / "dir_1"]

    assert sorted(diff.identical) == sorted(files)


def test_dirdiff_valuerror(tmp_path: pathlib.Path):
    """Test DirDiff with invalid arguments"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    create_snapshot(str(d1), str(snapshot_file1), walk=False)

    # snapshot 2
    snapshot_file2 = tmp_path / "2.snapshot"
    create_snapshot(str(d1), str(snapshot_file2), walk=False)

    with pytest.raises(ValueError):
        dirdiff = DirDiff(
            str(d1),
            str(snapshot_file2),
        )

    with pytest.raises(ValueError):
        dirdiff = DirDiff(str(snapshot_file1), str(d1 / "file_0"))


def test_snapshot_error(tmp_path: pathlib.Path):
    """Test snapshot with with existing file"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    # snapshot 1
    snapshot_file1 = tmp_path / "1.snapshot"
    create_snapshot(str(d1), str(snapshot_file1), walk=False)

    # snapshot 2
    with pytest.raises(ValueError):
        create_snapshot(str(d1), str(snapshot_file1), walk=False)


def test_dirsnapshot(tmp_path: pathlib.Path):
    """Test DirSnapshot methods"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    snapshot_db = tmp_path / "snapshot.db"
    snapshot = create_snapshot(
        str(d1), snapshot_db, walk=True, description="Test Snapshot"
    )
    assert is_snapshot_file(snapshot_db)
    assert snapshot.description == "Test Snapshot"
    assert snapshot.directory == str(d1)
    assert sorted(list(snapshot.files())) == sorted(files)
    assert type(snapshot.datetime) == datetime.datetime
    info = snapshot.info
    assert type(info) == SnapshotInfo
    assert info.description == "Test Snapshot"
    assert info.directory == str(d1)
    record = snapshot.record(str(d1 / "file_0"))
    assert type(record) == SnapshotRecord
    assert record.path == str(d1 / "file_0")
    assert record.is_file
    assert not record.is_dir

    record_dict = record.asdict()
    assert record_dict["path"] == str(d1 / "file_0")

    record_dict2 = json.loads(record.json())
    assert record_dict2["path"] == str(d1 / "file_0")

    records = list(snapshot.records())
    assert len(records) == len(files)


def test_dirsnapshot_load(tmp_path: pathlib.Path):
    """Test DirSnapshot methods when loaded from disk"""
    d1 = tmp_path / "dir1"
    d1.mkdir()
    files = populate_dir(d1)

    snapshot_db = tmp_path / "snapshot.db"
    snapshot_ = create_snapshot(
        str(d1), snapshot_db, walk=True, description="Test Snapshot"
    )
    assert is_snapshot_file(snapshot_db)

    snapshot = load_snapshot(snapshot_db)
    assert snapshot.description == "Test Snapshot"
    assert snapshot.directory == str(d1)
    assert sorted(list(snapshot.files())) == sorted(files)
    assert type(snapshot.datetime) == datetime.datetime
    info = snapshot.info
    assert type(info) == SnapshotInfo
    assert info.description == "Test Snapshot"
    assert info.directory == str(d1)
    record = snapshot.record(str(d1 / "file_0"))
    assert type(record) == SnapshotRecord
    assert record.path == str(d1 / "file_0")
    assert record.is_file
    assert not record.is_dir

    record_dict = record.asdict()
    assert record_dict["path"] == str(d1 / "file_0")

    record_dict2 = json.loads(record.json())
    assert record_dict2["path"] == str(d1 / "file_0")

    records = list(snapshot.records())
    assert len(records) == len(files)
