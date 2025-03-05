.. _terminology:

Terminology
===========

.. glossary::

    method
        Methods define the input, output, and params (parameters) of a step in the workflow.
        Methods can be defined by the user or imported from the HydroFlows library.
        The method must have a specific signature to be used in HydroFlows, see the :class:`hydroflows.workflow.Method` class.

    workflow
        A workflow is a sequence of methods that are executed in a specific order.
        The workflow is defined using the :class:`hydroflows.workflow.Workflow` class.

    rule
        A rule specifies one (or more in case of expand and repeat wildcards) specific instance(s) of a method in a workflow.
        A rule is created by adding a method to the workflow using the `add_rule` method of the workflow class.

    wildcards
        Wildcards are used to create multiple instances of a method in a workflow rule and allow for parallelization of the workflow.
        This way a method can be repeated for different input files, expand to multiple output files,
        or reduce over multiple input files. Wildcards keys and values need to be defined at
        the workflow level and used to create all instances of a method in a rule.

    engine
        The workflow engine is controls the execution of the workflow.
        Supported engines are the HydroFlows engine, SnakeMake, or CWL
