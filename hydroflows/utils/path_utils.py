"""Utils for model path operations."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

__all__ = ["cwd", "make_relative_paths", "rel_to_abs_path", "abs_to_rel_path"]


@contextmanager
def cwd(path: Path):
    """Change the current working directory to the root of the workflow."""
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


def make_relative_paths(data: Dict, src: Path, dst: Path) -> dict:
    """Replace existing file paths relative to src with paths relative to dst.

    Parameters
    ----------
    data : dict
        Dictionary with data parameters including file paths.
    src, dst : Path
        Source and destination paths.
    """
    data_out = dict()
    relpath = _get_rel_path(dst, src)
    for k, v in data.items():
        if isinstance(v, (str, Path)) and Path(v).is_absolute():
            try:
                v = (_get_rel_path(Path(v).parent, src) / Path(v).name).as_posix()
            except ValueError:
                continue
        if (
            isinstance(v, (str, Path))
            and Path(src, v).is_file()
            and not Path(dst, v).is_file()
        ):
            data_out[k] = (relpath / v).as_posix()
        else:
            # leave arg as is
            data_out[k] = v
    return data_out


def rel_to_abs_path(data: Dict, root: Path, keys: Optional[List[str]] = None) -> Dict:
    """Replace relative paths with absolute paths using root as base."""
    data_out = data.copy()
    if keys is None:
        keys = [key for key in data if isinstance(data[key], (str, Path))]
    for key in keys:
        if key in data and not Path(data[key]).is_absolute():
            data_out[key] = Path(root) / data[key]
    return data_out


def abs_to_rel_path(
    data: Dict, root: Path, keys: Optional[List[str]] = None, serialize=True
) -> Dict:
    """Replace absolute paths with relative paths using root as base."""
    data_out = data.copy()
    if keys is None:
        keys = [key for key in data if isinstance(data[key], (str, Path))]
    for key in keys:
        if key not in data or data[key] is None:
            continue
        try:
            data_out[key] = _get_rel_path(root, data[key])
            if serialize:
                data_out[key] = data_out[key].as_posix()
        except ValueError:
            continue
    return data_out


def _get_rel_path(dst: Path, src: Path) -> Path:
    commonpath = ""
    if os.path.splitdrive(src)[0] == os.path.splitdrive(dst)[0]:
        commonpath = os.path.commonpath([src, dst])
    if os.path.basename(commonpath) == "":
        raise ValueError("No common path between src and dst")
    relpath = os.path.relpath(src, start=dst)
    return Path(relpath)
