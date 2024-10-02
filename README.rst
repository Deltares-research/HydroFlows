.. _readme:

==========
HydroFlows
==========

|status| |license|

.. |status| image:: https://www.repostatus.org/badges/latest/wip.svg
   :alt: Project Status: WIP – Initial development is in progress, but there has not yet been a stable, usable release suitable for the public.

.. |license| image:: https://img.shields.io/github/license/Deltares/hydromt?style=flat
    :alt: License
    :target: https://github.com/Deltares-research/HydroFlows/blob/main/LICENSE

.. warning::
   This is a **work in progress** and not yet ready for use!

HydroFlows is a Python package for automated workflows for globally applicable flood risk assessments.
At its core, it contains a set of methods that can be called via command line interface (CLI) or Python API.
These are combined into `snakemake <https://snakemake.readthedocs.io>`_ workflows to perform a series of tasks that are common to flood risk assessments.

How to install
==============

To install HydroFlows, you can use either pixi (recommended for developers), pip or conda/mamba.
The package is not yet available on PyPi or conda-forge, so you need to install it from the GitHub repository.

Using pixi
----------

Pixi offers a project-centric approach for python environments and run commands.
Using the pixi.lock file the environment is reproducible and can be shared with others.

First, install pixi from https://pixi.sh/latest/
Then, clone the repository and install HydroFlows using pixi (this will also create an editable installation of HydroFlows):

.. code-block:: bash

   git clone git@github.com:Deltares-research/HydroFlows.git
   cd HydroFlows
   pixi install                # dev py3.11 installation from the lock file

   # optional commands (see "pixi run x" for more options)
   pixi run install-pre-commit # install pre-commit hooks
   pixi run html-docs          # build the documentation
   pixi run tests              # run all tests


To update the lock file and your environment after changes to the dependencies, run:

.. code-block:: bash

   pixi update

Using conda
-----------

To install HydroFlows using conda, you first need to clone the repository,
then create a conda environment file from the pyproject.toml and install all dependencies, and finally install HydroFlows:

.. code-block:: bash

   git clone git@github.com:Deltares-research/HydroFlows.git
   cd HydroFlows
   python make_env.py
   conda env create -f environment.yml
   conda activate hydroflows
   pip install .

Using pip
---------

Using pip you can install HydroFlows and its dependencies directly from GitHub.
We recommend you also create a virtual/conda environment (not shown below) in which you install the package.

.. code-block:: bash

   pip install git+https://github.com/Deltares-research/HydroFlows.git

How to use
==========

HydroFlows can be used via the command line interface (CLI) or via the Python API.
The CLI is the recommended way to start a new project and run workflows, while the Python API is more flexible and can be used to create custom workflows.

To create a new project directory, run:

.. code-block:: bash

   hydroflows init <project_dir> --region <region_file> --config <config_file>

This will create a new project directory with a default configuration file and a directory structure for input and output data.
To run a workflow in the project directory with snakemake, run:

.. code-block:: bash

   cd <project_dir>
   snakemake -s workflow/<workflow_name>.smk -c 1 --verbose

.. note::
   The workflows will be created from command line methods that are currently being established.
