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
   This is a **work in progress**!

Overview
========

**HydroFlows** aims to make it easy to create validated workflows using standardized methods and parse these to a workflow engine.
In HydroFlows, a workflow consists of methods that are chained together by connecting the file-based output of one method to the input of another.
While HydroFlows can also execute the workflows, it is recommended to use a workflow engine to manage the execution of the workflows
and to take advantage of the parallelization, scalability, and caching features of these engines.
Currently we support Snakemake_ or engines that support the Common Workflow Language (CWL_).

Why HydroFlows?
---------------

It can be challenging to create workflows, especially when these should be modular and flexible.
With HydroFlows, users can create workflows in a Python script and don't need to learn a new language or syntax.
Using a IDE such as VSCode_ method in- and outputs can easily be discovered, making it easy to chain methods together in a workflow.
Furthermore, method parameters are directly validated at initialization and connections between methods are validated when adding them to the workflow.
All these features make it easy to create and maintain workflows compared to other workflow engines.

HydroFlows for flood risk assessments
-------------------------------------

Currently, the available methods in HydroFlows are focused on flood risk assessments.
Methods include the automated setup of physics-based models such as Wflow_ and SFINCS_, statistical analysis, and impact assessments using Delft-FIAT_.
Many methods build on HydroMT_ and are backed up by a large stack of state-of-art global datasets to enable rapid assessments anywhere globally.
As the workflows are fully automated these can easily be replaced by local data  where available.
The final outcomes of the HydroFlows flood risk workflows are flood hazard and risk maps and statistics.
In addition a FloodAdapt_ instance can be created from the build models and event sets.

Getting Started
===============

How to install HydroFlows
-------------------------

To install HydroFlows, you can use either pixi_ or conda_.
The package is not yet available on PyPi or conda-forge, so you need to install it from the GitHub repository.

Using conda (for users)
^^^^^^^^^^^^^^^^^^^^^^^

We suggest using mamba_ as a faster alternative to conda, which is included in the miniforge_ Python distribution.
To install HydroFlows using conda, you first need to clone the repository,
then create a conda environment file from the pyproject.toml and install all dependencies,
and finally install HydroFlows:

.. code-block:: bash

   git clone git@github.com:Deltares-research/HydroFlows.git
   cd HydroFlows
   python make_env.py
   mamba env create -f environment.yml -n hydroflows
   conda activate hydroflows
   pip install .

Using pixi (for developers)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pixi offers a project-centric approach for python environments and run commands.
Using the pixi.lock file the environment is reproducible and can be shared with others.

First, install pixi using the instructions on the pixi_ website.
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


Acknowledgements
================

This library was created as part of the Horizon Europe UP2030_ (Grant Agreement Number 101096405)
and InterTwin_ (Grant Agreement Number 101058386) projects.


License
=======

MIT license, see the `LICENSE <LICENSE>`_ file for details.


.. _snakemake: https://snakemake.readthedocs.io/en/stable/
.. _CWL: https://www.commonwl.org/
.. _VSCode: https://code.visualstudio.com/
.. _Wflow: https://deltares.github.io/Wflow.jl/
.. _SFINCS: https://sfincs.readthedocs.org/
.. _Delft-FIAT: https://deltares.github.io/Delft-FIAT/
.. _HydroMT: https://deltares.github.io/hydromt/
.. _FloodAdapt: https://deltares-research.github.io/FloodAdapt/
.. _pixi: https://pixi.sh/latest/
.. _mamba: https://mamba.readthedocs.io/en/latest/
.. _conda: https://docs.conda.io/en/latest/
.. _miniforge: https://conda-forge.org/download/
.. _UP2030: https://up2030-he.eu/
.. _InterTwin: https://www.intertwin.eu/
