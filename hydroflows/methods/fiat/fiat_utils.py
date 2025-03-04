"""Utility of the FIAT methods."""
import re
from pathlib import Path
from shutil import copy

import tomli


def new_column_headers(
    columns: list | tuple,
    simple: bool = False,
):
    """Set the headers in the format of newer FIAT versions.

    Once HydroMT-FIAT has this functionality, this can be deleted.

    Parameters
    ----------
    columns : list | tuple
        The columns headers of the exposure data.
    simple : bool, optional
        Whether to return a simple conversion, i.e. everything lower case and
        whitespaces replaced by underscores. By default False.
    """
    new = dict(
        zip(
            columns,
            [item.lower().replace(" ", "_") for item in columns],
        )
    )
    if simple == True:
        return new

    # Update these headers which do not translate simply
    new.update(
        {
            "Extraction Method": "extract_method",
            "Ground Elevation": "ground_elevtn",
            "Ground Floor Height": "ground_flht",
        }
    )

    # Focus on the vulnerability functions headers
    re_fn = re.compile(r"^(.*)\sFunction:\s+(.*)$")
    re_max = re.compile(r"^Max Potential\s+(.*):\s+(.*)$")

    fn = {}
    for pattern, new_pattern in ((re_fn, "fn_{}_{}"), (re_max, "max_{}_{}")):
        found = list(filter(pattern.match, columns))
        for f in found:
            x = pattern.findall(f)
            string = new_pattern.format(*[item.lower() for item in x[0]])
            fn[f] = string

    new.update(fn)

    return new


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
