"""Small script to run all notebooks in the current directory using nbcovert."""

import os
from pathlib import Path

import papermill as pm
import argparse



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all notebooks in the examples and cases directories.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing executed notebooks in the output directory."
    )
    args = parser.parse_args()
    current_dir = Path(__file__).parent
    examples_dir = current_dir / "../examples"
    cases_dir = current_dir / "../cases"
    output_dir = Path(current_dir, "_examples")
    output_dir.mkdir(exist_ok=True)
    for nb in list(Path(examples_dir).glob("*.ipynb")) + list(Path(cases_dir).glob("**/*.ipynb")):
        nb_name = nb.name
        if Path(output_dir, nb_name).exists():
            if args.overwrite is False:
                print(f"Skipping {nb_name} (already executed)")
                continue
            else:
                Path(output_dir, nb_name).unlink()
        os.chdir(Path(nb).parent)
        print(f"Running {nb_name}")
        pm.execute_notebook(nb, output_path=output_dir / nb_name)
