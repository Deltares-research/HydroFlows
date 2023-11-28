# default nested folder structures for use in HydroFlows
import os
from typing import Union

models = [
    "wflow",
    "sfincs",
    "fiat"
]

data = {
    "wflow": ["input", "output"],
    "sfincs": ["input", "output"],
    "fiat": ["input", "output"]
}

domain_structure = {
    "data": data,
    "models": models,
}

def create_folders(
        root: str = ".",
        structure: Union[dict, list] = domain_structure
):
    """
    Setup a folder structure for a given domain

    Parameters
    ----------
    root : str, optional
        root folder (typically named as the spatial domain of the intended workflow

    Returns
    -------
    None

    """
    # first create root folder
    os.makedirs(root, exist_ok=True)
    if isinstance(structure, list):
        for k in structure:
            os.makedirs(
                os.path.join(root, k),
                exist_ok=True
            )
    else:
        # go one level deeper
        for k, v in structure.items():
            create_folders(
                root=os.path.join(root, k),
                structure=v
            )
    # Done