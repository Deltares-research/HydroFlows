from pathlib import Path

import pytest

from hydroflows.utils.path_utils import (
    abs_to_rel_path,
    make_relative_paths,
    rel_to_abs_path,
)


def test_make_relative_paths(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst" / "sub"
    src_file1 = src / "file1.txt"
    src_file2 = src / "file2.txt"
    dst_file1 = dst / "file1.txt"
    # create files
    src.mkdir(parents=True)
    dst.mkdir(parents=True)
    src_file1.write_text("file1")
    src_file2.write_text("file2")
    dst_file1.write_text("file1")
    data = {
        "file1": src_file1,  # abs
        "file2": src_file2.name,  # rel
        "other": "not_a_path",
    }
    expected = {
        "file1": "file1.txt",  # exists in dst
        "file2": "../../src/file2.txt",  # rel to src
        "other": "not_a_path",
    }
    result = make_relative_paths(data, src, dst)
    assert result == expected

    # no common path
    dst = Path("/Z/asd")
    with pytest.raises(ValueError, match="No common path"):
        make_relative_paths(data, src, dst)


def test_rel_to_abs_path():
    data = {
        "file1": "relative/path/to/file1.txt",
        "file2": "/absolute/path/to/file2.txt",
    }
    root = Path("/base/root")
    expected = {
        "file1": Path("/base/root/relative/path/to/file1.txt"),
        "file2": Path("/absolute/path/to/file2.txt"),
    }
    result = rel_to_abs_path(data, root)
    assert result == expected


def test_abs_to_rel_path():
    data = {
        "file1": "/base/root/relative/path/to/file1.txt",
        "file2": "/absolute/path/to/file2.txt",
        "file3": "/base/root/test/path/to/file3.txt",
        "other": "not_a_path",
    }
    root = Path("/base/root/test")
    expected = {
        "file1": "../relative/path/to/file1.txt",
        "file2": "/absolute/path/to/file2.txt",
        "file3": "path/to/file3.txt",
        "other": "not_a_path",
    }
    result = abs_to_rel_path(data, root)
    assert result == expected
