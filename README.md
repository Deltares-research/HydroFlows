![Project Status: WIP – Initial development is in progress, but there has not yet been a stable, usable release suitable for the public.](https://www.repostatus.org/badges/latest/wip.svg)

# HydroFlows

> Note: This is a **work in progress** and not yet ready for use!

HydroFlows is a Python package for automated workflows for globally applicable flood risk assessments.
At its core it contains a set of methods that can be called via command line interface (CLI) or Python API.
These are combined into [snakemake](https://snakemake.readthedocs.io) workflows to perform a series of tasks that are common to flood risk assessments.

## How to install

To install HydroFlows, you can use either pip or conda.
The package is not yet available on PyPi or conda-forge, so you need to install it from the GitHub repository.

### Using conda

To install HydroFlows using conda, you first need to clone the repository,
then create a conda environment file from the pyproject.toml and install all dependencies, and finally install HydroFlows:

```bash
git clone git@github.com:Deltares-research/HydroFlows.git
cd HydroFlows
python make_env.py
conda env create -f environment.yml
pip install .
```

### Using pip

Using pip you can install HydroFlows and its dependencies directly from github.
We recommend you also create a virtual/conda environment (not shown below) in which you install the package.

```bash
pip install git+https://github.com/Deltares-research/HydroFlows.git
```

## How to use
HydroFlows can be used via the command line interface (CLI) or via the Python API.
The CLI is the recommended way to start a new project and run workflows, while the Python API is more flexible and can be used to create custom workflows.

To create a new project directory, run:

```bash
hydroflows init <project_dir> --region <region_file> --config <config_file>
```

This will create a new project directory with a default configuration file and a directory structure for input and output data.
To run a workflow in the project directory with snakemake, run:

```bash
cd <project_dir>
snakemake -s workflow/<workflow_name>.smk -c 1 --verbose
```
