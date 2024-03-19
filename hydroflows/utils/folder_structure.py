"""Method to create a project folder structure."""

# TODO: should we use cookiecutter instead?

import os
from distutils.dir_util import copy_tree
from pathlib import Path

__all__ = ["create_folders", "copy_templates"]

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"



def create_folders(
    root: Path,
    models: list = ["wflow", "sfincs", "fiat"]
) -> None:
    """
    Create and setup a folder structure for a project.

    Parameters
    ----------
    root : str, optional
        project root folder
    models : list, optional
        list of model names to create folders for
    """
    folders = {
        "bin": models,
        "data": ["input", "output"],
        "models": models,
        "results": [],
        "workflow": [
            # "envs",
            "hydromt_config",
            # "methods",
            # "notebooks",
            "snake_config",
            "scripts"
        ],
    }

    def _makedir(root, subfolders) -> None:
        if isinstance(subfolders, list):
            if len(subfolders) > 0:
                for sf in subfolders:
                    os.makedirs(root / sf, exist_ok=True)
            else:
                os.makedirs(root, exist_ok=True)
        elif isinstance(subfolders, dict):
            for k, v in subfolders.items():
                _makedir(root / k, v)

    # make sure root is a Path object
    root = Path(root)
    _makedir(root, folders)

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
