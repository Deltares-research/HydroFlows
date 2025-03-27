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
   Deltares does not provide any support for this software.
   The software is provided as is and is not suitable for production use.

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
In addition a FloodAdapt_ instance can be created from the built models and event sets.

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
.. _UP2030: https://up2030-he.eu/
.. _InterTwin: https://www.intertwin.eu/
