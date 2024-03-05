# TODO move this into a cookiecutter template?
# default nested folder structures for use in hydroflows

""" 
├── .gitignore
├── environment.yml
├── README.md
├── LICENSE.md
├── workflow
│   ├── methods
|   │   ├── module1.smk
|   │   └── module2.smk
│   ├── envs
|   │   ├── tool1.yaml
|   │   └── tool2.yaml
│   ├── scripts
|   │   ├── script1.py
|   │   └── script2.R
│   ├── notebooks
|   │   ├── notebook1.py.ipynb
|   │   └── notebook2.r.ipynb
|   └── Snakefile
├── config
│   ├── config.yaml
│   └── some-sheet.tsv
├── data
│   ├── input
│   └── output
├── models
│   ├── wflow
|   │   └── {region1}
|   │       ├── staticmaps.nc
|   │       ├── wflow_sbm_default.toml 
|   │       ├── hydromt_wflow.yaml
|   │       └── simulations
|   │           └── {sim1}
|   │               ├── wflow_sim1.toml
|   │               └── forcing.nc
│   ├── sfincs
|   │   └── {region1}
|   │       ├── sfincs.xxx
|   │       ├── sfincs.inp
|   │       └── simulations
|   │           └── {sim1}
|   │               ├── sfincs.xxx
|   │               └── sfincs.inp
│   └── fiat
├── results
└── resources

"""


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