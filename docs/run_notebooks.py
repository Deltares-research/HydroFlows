"""Small script to run all notebooks in the current directory using nbcovert."""

import os
from pathlib import Path

import papermill as pm



if __name__ == "__main__":
    current_dir = Path(__file__).parent
    examples_dir = current_dir / "../examples"
    output_dir = Path(current_dir, "_examples")
    output_dir.mkdir(exist_ok=True)
    os.chdir(examples_dir)
    for nb in Path(examples_dir).glob("*.ipynb"):
        nb_name = nb.name
        print(f"Running {nb_name}")
        pm.execute_notebook(nb, output_path=output_dir / nb_name)
