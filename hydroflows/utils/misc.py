"""Some extra utilty."""
import shutil
from pathlib import Path

import yaml


def adjust_config(
    config: Path | str,
    extra: Path | None = None,
    **kwargs,
):
    """Adjust the config based on extra input."""
    with open(config, "r") as _r:
        cfg = yaml.safe_load(_r)

    # Update from custom configurations file
    if extra is not None:
        with open(extra, "r") as _r:
            ext = yaml.safe_load(_r)
            cfg.update(ext)

    # Update with the kwargs
    cfg.update(kwargs)

    # Write it back to the drive
    with open(config, "w") as _w:
        yaml.dump(cfg, _w, sort_keys=False)


def check_file_path(ctx, _, path):
    """Check the file path in a cli friendly way."""
    if path is None:
        return
    root = Path.cwd()
    path = Path(path)
    if not path.is_absolute():
        path = Path(root, path)
    if not (path.is_file() | path.is_dir()):
        raise FileNotFoundError(f"{str(path)} is not a valid path")
    return path


def copy_single_file(
    target: Path | str,
    dest: Path | str,
):
    """Copy as single file from one location to another."""
    shutil.copy2(
        target,
        dest,
    )
