.. _terminology:

Terminology
===========

.. glossary::

    method
        Methods define and validate the input, output, and params (parameters) of a step in the workflow.
        Methods also define the logic of what is executed, which can be a simple command line call or a complex Python function.
        We distinguish between normal, expand, and reduce methods, see also :ref:`define_method` section.
        HydroFlows contains a library of methods focussing on flood risk assessments, but users can also define their own methods.
        All methods must have a specific signature to be used in HydroFlows, for more information see the :class:`~hydroflows.workflow.Method` class and :ref:`add_own_methods` section.

    rule
        A rule is a wrapper around a method to be run in the context of a workflow.
        The rule is responsible for detecting wildcards and evaluating them based on the workflow wildcards.
        A rule is created by adding a method to the workflow using the :meth:`~hydroflows.workflow.Workflow.create_rule` method of the workflow class.
        For more information see the :ref:`compose_workflow` section.

    wildcards
        Wildcards are used to create multiple instances of a method in a rule and allow for parallelization of the workflow.
        Wildcards are defined with ``{<wildcard_name>}`` in the input or output file paths of a method and their values are set in the :attr:`~hydroflows.workflow.Workflow.wildcards` attribute.
        Normal methods can repeated for multiple of the same input files or different values of the same param if the same wildcard is set on the input and/or params, and output files, these are called **repeat** wildcards.
        Expand methods will generate a new wildcard on one or more output files to create multiple of the same output files, these are called **expand** wildcards.
        Reduce methods require a wildcard on the input files to reduce over multiple of the same input files, these are called **reduce** wildcards.
        For more information see the :ref:`compose_workflow` section and :class:`~hydroflows.workflow.Wildcards` class.

    workflow
        A workflow is a sequence of rules that are executed in a specific order.
        A workflow is initialized with a root directory and optional configuration and wildcards.
        Then, rules can be added to the workflow which are validated on the fly.
        A workflow can be visualized using a `rulegraph` and exported to a workflow engine.
        The workflow is defined using the :class:`~hydroflows.workflow.Workflow` class.
        For more information see the :ref:`compose_workflow` section.

    configuration
        The workflow configuration contains settings for the workflow rules which will be saved to a separate configuration file when exporting to a workflow engine.
        This way the exported workflow can still to some extend be configured by the user.
        A user can define the configuration using the :class:`~hydroflows.workflow.WorkflowConfig` class.
        These parameters can be passed to the methods using a reference object, typically created using the
        :meth:`~hydroflows.workflow.Workflow.get_ref` method

    engine
        The workflow engine is controls the execution of the workflow.
        Supported engines are the HydroFlows engine, SnakeMake_, or CWL_
