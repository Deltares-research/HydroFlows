.. _ug_create:

Creating a workflow file
========================

.. _workflow_template:

Workflow template
-----------------

The starting point for a workflow is in most cases a workflow template. This is a ``yaml`` formatted file, that
contains the different steps or "rules" of a workflow with all required inputs. Let's have a look at an example
workflow template file.

.. literalinclude:: ../../examples/sfincs_pluvial.yml
    :language: yaml

Below we describe the most important components, following this example:

* ``config``: here a number of overall settings may be defined that can be re-used within the workflow's rules.
* ``rules``: a functionality that generates output(s) from input(s) and parameters with a certain piece of work. Each
  rule consists of a method that codifies how output(s) are generated from input(s) and parameters. Arguments passed
  to rules can be inherited from other rules. Rules can also "expand" or "reduce". We explain more about this later.
  The coherence between rules with their expansions and reductions results in a graph for the workflow.

We can also see that each subsection under ``rules`` has two arguments

* ``method``: the intelligence behind the rule, a set of instructions defining how output(s) are generated from input
  (s) and parameters. This can be anything, for instance preprocessing of gridded forcing records into model specific
  event inputs, generation of a full model from a set of defined static input datasets, running of a model (which may
  have been derived in a predecessing rule), postprocessing of a model result in a nice looking graph or map, etcetera.
* ``kwargs``: stands for "keyword arguments". Each method requires certain parameters, which must be defined under the
  ``kwargs`` section as separate inputs. For each method, certain specific inputs are needed, and some may be
  optional. More about this is described below.

To know which methods are available and which ``kwargs`` each methods has (mandatory and optional), you have to
consult the :ref:`API <api>` section, more specifically the part on methods. For instance the
method ``pluvial_design_events`` is described under the :ref:`rainfall methods <api_rainfall>`. It shows that it
generates pluvial design events, and that it requires ``precip_nc`` (path to rainfall time series) and ``rps`` (return
periods for which to derive rainfall events) as inputs. Each method is parsed to a ``Method`` instance and from the
``kwargs`` it is defined what the inputs, outputs and parameters of the method should be. Note that in the method API
description, several additional keyword arguments may be provided that are used as additional inputs, and that these
may be described under the method's ``Params``. For instance, In ``kwargs`` you could add ``plot_fig: False`` to the
method to suppress plotting of the hyetographs resulting from this method.

Creating a workflow file from the template in a selected language
-----------------------------------------------------------------

Even though the workflow file can be :ref:`run <run_workflow>` directly from HydroFlows, it is in most cases required
to translate the workflow into a typical workflow language such as Snakemake. This is because e.g. Snakemake offers
many additional functionalities to run workflow much more efficiently than HydroFlows. For instance, in Snakemake you
may provide arguments that allow you to allocate certain resources to rules, or balance loads of jobs to several
subprocesses or even nodes on a HPC cluster. This becomes necessary when you wish to compute a large number of
permutations of events (e.g. ensemble forecast, multi-climate, or compound events sets) or simply a very large
event-set (e.g. 1000s of synthetic events).

.. note::

    Currently we only support Snakemake as workflow language. Soon we will also support CWL and we are investigating
    Argo.

.. tab-set::

    .. tab-item:: CLI

        The CLI contains a separate ``--help`` for the ``create`` command.

        .. code-block:: shell

            $ hydroflows create --help

        .. program-output:: hydroflows create --help

        This shows that to create a workflow, a workflow template is needed as described :ref:`here
        <workflow_template>`. Running the command with the above template (see ``examples/sfincs_pluvial.yml``) as
        follows:

        .. code-block:: shell

            $ hydroflows create sfincs_pluvial.yml

        yields a file ``sfincs_pluvial.smk`` which contains a Snakemake (default) workflow which you can then implement
        in a compute environment of choice.

        .. literalinclude:: ../../examples/sfincs_pluvial.smk
            :language: yaml

        The earlier mentioned wildcards and their expansion and reduction are parsed
        automatically. The connections between the rules is organized via their inputs and outputs.

    .. tab-item:: API

        Within the API, a workflow template file can be loaded into a ``Workflow`` instance as follows:

        .. code-block:: python

            from hydroflows import Workflow

            workflow = Workflow.from_yaml("sfincs_pluvial.yml")
            print(workflow)

        which returns

        .. program-output:: python user_guide/read_workflow.py

        The workflow can also be built up from scratch by starting an empty workflow, creating rules that use each
        other's outputs as inputs and adding these rules to the workflow consecutively. We here show that until the
        ``sfincs_run`` rule for brevity:

        .. literalinclude:: setup_workflow.py
            :language: python

        A few things worth noting:

        * ``WorkflowConfig`` provides the general configuration options
        * ``workflow.get_ref`` is used to ensure outputs of one rule are made inputs to a next rule
        * input/output intelligence can also be directly derived from a rule under ``<rule>.output``.
        * wildcard names can be defined within each rule (e.g. ``"pluvial_event"``).

        Writing to snakemake can easily be done as follows:

        .. code-block:: python

            workflow.to_snakemake(f"sfincs_pluvial.smk")

.. _run_workflow:

Running a workflow
------------------
The workflow can be run in your local environment. This does not yield scalability as would be the case if you use
e.g. Snakemake or CWL. This can be useful for instance to test your workflow. Also dry-running is possible to see if
the input-output logic is correct.

.. tab-set::

    .. tab-item:: CLI

        .. note::

            Dry running is not yet possible on CLI.

        You may run the workflow directly as follows:

        .. code-block:: shell

            $ hydroflows run sfincs_pluvial.yaml

    .. tab-item:: API

        Dry-running in the API can be done as follows:

        .. code-block:: python

            from hydroflows import Workflow

            workflow = Workflow.from_yaml('sfincs_pluvial.yaml')
            workflow.run(dryrun=True)

            workflow.run()

        Running in the API can be done as follows:

        .. code-block:: python

            from hydroflows import Workflow

            workflow = Workflow.from_yaml('sfincs_pluvial.yaml')
            workflow.run()

This will execute all steps in your workflow on your local environment. Naturally make sure that the right python
environment is activated and that any executables you may need are available and specified.
