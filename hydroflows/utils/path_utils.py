"""Utils for model path operations."""

import os
from os.path import isfile, join
from pathlib import Path


def make_relative_paths(config: dict, src: Path, dst: Path) -> dict:
    """Return a config where existing file paths are replaced with relative paths.

    Parameters
    ----------
    config : dict
        Dictionary with config parameters including file paths.
    src, dst : Path
        Source and destination paths.
    """
    config_kwargs = dict()
    commonpath = ""
    if os.path.splitdrive(src)[0] == os.path.splitdrive(dst)[0]:
        commonpath = os.path.commonpath([src, dst])
    if os.path.basename(commonpath) == "":
        raise ValueError("src and dst must have a common path")
    relpath = os.path.relpath(commonpath, dst)
    for k, v in config.items():
        if (
            isinstance(v, (str, Path))
            and isfile(join(src, v))
            and not isfile((join(dst, v)))
        ):
            config_kwargs[k] = join(relpath, v)
        else:
            # leave arg as is
            config_kwargs[k] = v
    return config_kwargs
