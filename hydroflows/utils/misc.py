"""Some extra utilty."""
import shutil
from pathlib import Path

import yaml


def adjust_config(
    config: Path | str,
    extra: Path | None = None,
    **kwargs,
):
    """Adjust the config based on extra input.

    Fairly simple way of merging two config files. This will become \
more sophisticated on a later date.

    Parameters
    ----------
    config : Path | str
        Path to the current config file.
    extra : Path | None, optional
        Path to the users file with custom settings.
    kwargs : dict
        Extra separate entries to be included.
    """
    with open(config, "r") as _r:
        cfg = yaml.safe_load(_r)

    # Update from custom configurations file
    if extra is not None:
        with open(extra, "r") as _r:
            ext = yaml.safe_load(_r)
            cfg.update(ext)

    # Update with the kwargs
    # TODO find a better way of resolving this.
    cfg.update(kwargs)

    # Write it back to the drive
    with open(config, "w") as _w:
        yaml.dump(cfg, _w, sort_keys=False)


def copy_single_file(
    target: Path | str,
    dest: Path | str,
):
    """Copy as single file from one location to another."""
    shutil.copy2(
        target,
        dest,
    )


class SafeFormatDict(dict):
    """A dictionary that returns the key if the key is not found."""

    def __missing__(self, key):
        return "{" + key + "}"
