.. _terminology:

Terminology
===========

.. glossary::

    method
        Methods define the input, output, and params (parameters) of a step in the workflow.
        Methods can be defined by the user or imported from the HydroFlows library.
        The method must have a specific signature to be used in HydroFlows,
        for more information see the :class:`~hydroflows.workflow.Method` class.

    workflow
        A workflow is a sequence of methods that are executed in a specific order.
        The workflow is defined using the :class:`~hydroflows.workflow.Workflow` class.

    rule
        A rule specifies one (or more in case of expand and repeat wildcards) specific instance(s) of a method in a workflow.
        A rule is created by adding a method to the workflow using the :meth:`~hydroflows.workflow.Workflow.add_rule` method of the workflow class.

    wildcards
        Wildcards are used to create multiple instances of a method in a rule and allow for parallelization of the workflow.
        With wildcards a method can be repeated for different input files, expanded to multiple output files,
        or reduced over multiple input files.
        Wildcard names and values need to be defined at the workflow level and set prior to adding a rule with a wildcards on their input.
        Wildcards are stored in the :attr:`~hydroflows.workflow.Workflow.wildcards` attribute.
        For more information see the :class:`~hydroflows.workflow.Wildcards` class.

    configuration
        The workflow configuration stores all workflow parameters and input files which are not output of another rule.
        A user can also predefine parameters using the :class:`~hydroflows.workflow.WorkflowConfig` class.
        These parameters can be passed to the methods using a reference object, typically created using the
        :meth:`~hydroflows.workflow.Workflow.get_ref` method

    engine
        The workflow engine is controls the execution of the workflow.
        Supported engines are the HydroFlows engine, SnakeMake, or CWL
