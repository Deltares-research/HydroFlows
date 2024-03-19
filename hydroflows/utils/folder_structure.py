"""Method to create a project folder structure."""

# TODO: should we use cookiecutter instead?

import os
from distutils.dir_util import copy_tree
from pathlib import Path

__all__ = ["create_folders", "copy_templates"]

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

models = [
    "wflow",
    "sfincs",
    "fiat"
]

folders = {
    "bin": models,
    "data": {m: ["input", "output"] for m in models},
    "models": models,
    "results": None,
    "workflow": None,
}


def create_folders(
        root: Path,
        folders: dict = folders
) -> None:
    """
    Create and setup a folder structure for a project.

    Parameters
    ----------
    root : str, optional
        project root folder
    """
    # make sure root is a Path object
    root = Path(root)
    # first create root folder
    os.makedirs(root, exist_ok=True)
    # create subfolders
    for k, v in folders.items():
        if v is None:
            os.makedirs(root / k, exist_ok=True)
        else:
            for vv in v:
                os.makedirs(root / k / vv, exist_ok=True)
    # Done

def copy_templates(
        root: Path,
) -> None:
    """
    Copy templates to the project folder.

    Parameters
    ----------
    root : str, optional
        project root folder
    """
    # copy all files in TEMPLATE_DIR to root
    copy_tree(TEMPLATE_DIR, root)
