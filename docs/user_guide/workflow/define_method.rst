.. _define_method:

Define methods
==============

Using predefined methods
------------------------

Methods are the building blocks of a :term:`workflow` in HydroFlows.
Methods define the ``input``, ``output``, and ``params`` (parameters) of a step in the workflow.
The input and output attributes contain only file paths to the input and output files.
The params attribute contains the parameters of the method, which can be used to control
the behavior of the method.

Each method is initialization with a minimal set of required arguments which can be found
in the signature of the method and its API documentation.
The arguments typically are the input files and selected params. Optional params can be set
using keyword arguments and explored by linking to the method Params class.
The method output files are generated based on these arguments and stored in the output
attribute of the method.
At initialization, the input, output, and params are validated using the `pydantic`_ library.

After initialization the method output files can be explored using the `output` attribute.
These output files can directly used as input for other methods in the workflow,
see :ref:`compose_workflow` section.

.. ipython:: python

    from hydroflows.methods.sfincs import SfincsBuild

    # initialize a method
    sfincs_build = SfincsBuild(
        region="data/region.shp",
        sfincs_root="models/sfincs",
        config="config/hydromt_sfincs.yml",
        catalog_path="data/data_catalog.yml",
    )

    # explore the output files
    sfincs_build.output

Usually, the method is run as part of a :ref:`workflow` or :ref:`rule` and executed from the
workflow root directory, see :ref:`execute_workflow` and :ref:`parse_to_engine` sections.
It is however also possible to run the method directly using the `run` method of the method class.
This is only possible if all inputs are available and no :ref:`wildcards` are present in the input
or params attributes. In this case the method is executed from the current working directory.

.. _expand_reduce_methods::

Expand and reduce methods
-------------------------

There are two special types of methods that can be used to create multiple output files from a single
set of input files (expand) or to create a single output file from multiple input files (reduce).
These methods are called `ExpandMethod` and `ReduceMethod` and are subclasses of the `Method` class.
The `ExpandMethod` class generates one or more :ref:`wildcards` on the output files which can be used
in subsequent rules to expand the workflow over multiple output files.

Using python scripts as methods
-------------------------------

Python scripts can directly be added to a workflow using the :class:`~hydroflows.methods.script.ScriptMethod` class.
Note that this class does not provide any validation of the input, output, or parameters as their types are not known.
The `ScriptMethod` class is useful for adding simple scripts to a workflow that do not necessarily need validation.

.. ipython:: python

    from hydroflows.methods.script import ScriptMethod

    # initialize a method
    script_method = ScriptMethod(
        script="scripts/my_script.py",
        input={"input1": "data/input1.tif"},
        output={"output1": "data/output1.tif"},
    )

    # explore the output files
    script_method.output

To develop your own methods which do get validated, users should use the HydroFlows :class:`hydroflows.workflow.Method` class.
For more information on how to create your own methods, see the :ref:`add_own_methods` section.

.. Note::
    The `ScriptMethod` class currently only works well for scripts with hardcoded input and output files and no parameters.
    In combination with the `SnakeMake` engine, the `ScriptMethod` class can be used to pass the input, output, and params
    to the script using the global `snakemake` object, see the :ref:`snakemake` documentation for more information.
