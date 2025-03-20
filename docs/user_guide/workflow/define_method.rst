.. _define_method:

Define a method
===============

Using predefined methods
------------------------

Methods are the building blocks of a :term:`workflow` in HydroFlows.
Methods define the ``input``, ``output``, and ``params`` of a step in the workflow.
The input and output attributes contain only paths to the input and output files.
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

In the example below we initialize a method which is created for demonstration purposes only.
Printing the method shows all input, output and params fields of the method.

.. ipython:: python

    from hydroflows.methods.dummy import RunDummyEvent
    import logging

    # setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

    # initialize a method
    method = RunDummyEvent(
        event_csv="events/event1.csv",
        settings_toml="settings.toml",
        output_dir="model/event1",
        model_exe="bin/model.exe"
    )

    # explore the method input, output and params
    print(method)

Usually, the method is run as part of a :term:`workflow` or :term:`rule` and executed from the
workflow root directory, see :ref:`execute_workflow` and :ref:`parse_to_engine` sections.
It is however also possible to run the method directly using the `run` method of the method class.
This is only possible if all inputs are available and no :term:`wildcards` are present in the input
or params attributes. In this case the method is executed from the current working directory.

.. _expand_reduce_methods:

Expand and reduce methods
-------------------------

There are two special types of methods that can be used to create multiple output files from a single
set of input files (expand) or to create a single output file from multiple input files (reduce).
These methods are called `ExpandMethod` and `ReduceMethod` and are subclasses of the `Method` class.
The `ExpandMethod` class generates one or more :term:`wildcards` on the output files which can be used
in subsequent rules to expand the workflow over multiple output files. These can be explored by
printing the method as in the example below.
The wildcard name and values are defined in the method and stored in the `ExpandMethod.expand_wildcards` attribute, see below.
Which method arguments are used to define the name and values is described in the documentation.
An info logging message is printed with the wildcard name and values.


.. ipython:: python

    from hydroflows.methods.dummy import PrepareDummyEvents

    # initialize a method
    method = PrepareDummyEvents(
        timeseries_csv="data/timeseries.csv",
        output_dir="output",
        rps=[1,5,10,50,100],
    )

    # Check the method expand_wildcards
    print(method.expand_wildcards)

    # Note the method type and expand_wildcards
    print(method)


# TODO add example for ReduceMethod


.. _python_script:

Using python scripts as methods
-------------------------------

To make full use of the HydroFlows methods, these should be implemented following the HydroFlows ``Method`` api, see also :ref:`add_own_methods` section.
However, python scripts can directly be added to a workflow using the :class:`~hydroflows.methods.script.ScriptMethod` class.
This class does not provide any validation of the input, output, or parameters as their types are not known.
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
    print(script_method)

.. Note::
    The `ScriptMethod` class currently only works well for scripts with hardcoded input and output files and no parameters.
    In combination with the `SnakeMake` engine, the `ScriptMethod` class can be used to pass the input, output, and params
    to the script using the global `snakemake` object, see the snakemake_ documentation for more information.


Define a custom method
----------------------

To make full use of the HydroFlows methods, these should be implemented following the HydroFlows ``Method`` api.
More information on how to create a custom method can be found in the :ref:`add_own_methods` section.
