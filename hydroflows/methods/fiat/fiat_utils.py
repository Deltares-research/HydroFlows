"""Utility of the FIAT methods."""
from pathlib import Path
from shutil import copy

import tomli


def copy_fiat_model(src: Path, dest: Path) -> None:
    """Copy FIAT model files.

    Parameters
    ----------
    src : Path
        Path to source directory.
    dest : Path
        Path to destination directory.
    """
    if not dest.exists():
        dest.mkdir(parents=True)
    with open(src / "settings.toml", "rb") as f:
        config = tomli.load(f)
    with open(src / "spatial_joins.toml", "rb") as f:
        spatial_joins = tomli.load(f)
    fn_list = []
    fn_list.append(config["vulnerability"]["file"])
    fn_list.append(config["exposure"]["csv"]["file"])
    fn_list.extend([v for k, v in config["exposure"]["geom"].items() if "file" in k])
    for areas in spatial_joins["aggregation_areas"]:
        fn_list.append(areas["file"])
    for file in fn_list:
        dest_fn = Path(dest, file)
        if not dest_fn.parent.exists():
            dest_fn.parent.mkdir(parents=True)
        copy(src / file, dest_fn)
    copy(src / "settings.toml", dest / "settings.toml")
    copy(src / "spatial_joins.toml", dest / "spatial_joins.toml")
