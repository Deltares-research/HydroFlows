Getting Started
===============

How to install HydroFlows
-------------------------

To install HydroFlows, you can use either pip_, pixi_ or conda_.
The package is not yet available on PyPi or conda-forge, so you need to install it from the GitHub repository.
Note that you need to have git_ installed on your system to clone the repository.

The library installs only the core submodules by default.
To install all flood risk methods, you can install the package with the extra `methods` dependencies.

Using conda (or mamba)
^^^^^^^^^^^^^^^^^^^^^^

We suggest using mamba_ as a faster alternative to conda, which is included in the miniforge_ Python distribution.
To install HydroFlows using conda, you first need to clone the repository,
then create a conda environment file from the pyproject.toml and install all dependencies, and finally install HydroFlows.
Here we install the `methods` and `extra` dependencies to be able to use all flood risk methods.
To develop we recommend using the or `full` profile which includes all optional dependencies.

.. code-block:: bash

   git clone git@github.com:Deltares-research/HydroFlows.git
   cd HydroFlows
   python make_env.py methods,extra -n hydroflows
   mamba env create -f environment.yml
   conda activate hydroflows
   pip install .


Using pip
^^^^^^^^^

Pip allows you to install HydroFlows directly from the GitHub repository.
We suggest you install HydroFlows in a conda environment with graphiz (and git).
Without a conda install of graphviz, the plotting methods will not work.

To install HydroFlows using pip in a new conda environment, run the following commands:

.. code-block:: bash

   conda create -n hydroflows python=3.11 git graphviz -c conda-forge
   conda activate hydroflows
   pip install "hydroflows[methods,extra] @ git+https://github.com/Deltares-research/HydroFlows.git"


Using pixi
^^^^^^^^^^

Pixi offers a project-centric approach for python environments and run commands.
Using the pixi.lock file the environment is reproducible and can be shared with others.

First, install pixi using the instructions on the pixi_ website.
Then, clone the repository and install HydroFlows using pixi (this will also create an editable installation of HydroFlows):

.. code-block:: bash

   git clone git@github.com:Deltares-research/HydroFlows.git
   cd HydroFlows
   pixi install                # default (methods,extra) py3.11 installation from the lock file


Using pixi (for developers)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install HydroFlows for development, you can use the `full` profile which includes all optional dependencies.
This will install all dependencies and create an editable installation of HydroFlows.

.. code-block:: bash

   git clone git@github.com:Deltares-research/HydroFlows.git
   cd HydroFlows
   pixi install -e full        # full dev py3.11 installation from the lock file

   # optional commands (see "pixi run x" for more options)
   pixi run -e full install-pre-commit # install pre-commit hooks
   pixi run -e full tests              # run all tests
   pixi run -e full html-docs          # build the documentation


To update the lock file and your environment after changes to the dependencies, run:

.. code-block:: bash

   pixi update


How to use HydroFlows
---------------------

HydroFlows is designed to create workflows using python scripts and parse these to a workflow engine like snakemake.
The example below shows how two methods can be chained together in a workflow and parsed to Snakemake.
More information on how to use HydroFlows including several examples can be found in the online user documentation.

.. code-block:: python

   from hydroflows import Workflow
   from hydroflows.methods import sfincs

   # create a workflow
   wf = Workflow(root="./my_workflow_root", name="my_workflow")

   # initialize a method and add it to the workflow
   sfincs_build = sfincs.SfincsBuild(
      region="data/region.shp",
      sfincs_root="models/sfincs",
      config="config/hydromt_sfincs.yml",
      catalog_path="data/data_catalog.yml",
   )
   wf.create_rule(sfincs_build, rule_id="sfincs_build")

   # initialize a second method and add it to the workflow
   sfincs_run = sfincs.SfincsRun(
      sfincs_inp=sfincs_build.output.sfincs_inp,
      run_method="exe",
      sfincs_exe="bin/sfincs/sfincs.exe"
   )
   wf.create_rule(sfincs_run, rule_id="sfincs_run")

   # parse the workflow to Snakemake, this will save a ./my_workflow_root/Snakefile
   wf.to_snakemake()


.. _pip: https://pip.pypa.io/en/stable/
.. _pixi: https://pixi.sh/latest/
.. _conda: https://docs.conda.io/en/latest/
.. _mamba: https://mamba.readthedocs.io/en/latest/
.. _miniforge: https://conda-forge.org/download/
.. _git: https://git-scm.com/
