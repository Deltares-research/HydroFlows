.. _ug_create:

Creating a workflow file
========================

.. _workflow_template:

Workflow script
---------------

The starting point for a workflow is in most cases a script that assembles all tasks and general configuration options.
The script is written in python and we recommend to gradually expand the script Let's have a look at an example
workflow template file.

.. literalinclude:: ../../examples/pluvial_hazard.py
    :language: python

Below we describe the most important components, following this example:

* ``WorkflowConfig``: here a number of overall static settings may be defined that can be re-used within the workflow's
  rules. Here an executable and a set of event return periods are defined.
* ``Workflow``: this is the workflow object, which eventually holds all tasks and connections. You can see that the
  variable `w` contains your workflow instance in this example.
* ``w.add_rule``: a functionality that adds a rule instance to your workflow. A rule generates output(s) from input(s)
  and parameters with a certain piece of work. Examples here include ``GetERA5Rainfall``, ``PluvialDesignEvents``,
  and so on. It can be anything, for instance preprocessing of gridded forcing records into model specific
  event inputs, generation of a full model from a set of defined static input datasets, running of a model (which may
  have been derived in a predecessing rule), postprocessing of a model result in a nice looking graph or map, etcetera.

If you look carefully at each line with ``add_rule``, and without considering the exact syntax for each rule, you can
see that this specific workflow contains the following rules:

* ``get_rainfall``: retrieve rainfall data of the ERA5 reanalysis for a region defined in a geojson file and for a
  given time period. The geojson file belongs to a SFINCS inundation model, that should be pre-existing. With more
  complex workflows, you can also build the SFINCS model as part of the workflow.
* ``pluvial_events``: derive events for different return periods from the rainfall data.
* ``sfincs_pre``: update the rainfall forcing of the sfincs model (done per event).
* ``sfincs_run``: run the sfincs model for the events.

Each rule consists of a method that codifies how output(s) are generated from input(s) and parameters.

You can
also see that arguments in certain rules can be inherited from other rules, e.g.

.. code-block:: python

    sfincs_pre = SfincsUpdateForcing(
        sfincs_inp=sfincs_root / "sfincs.inp",
        event_yaml=pluvial_events.output.event_yaml,
        event_name="{event}",
    )

Here, an output from ``pluvial_events``, defined by ``pluvial_events.output.event_yaml``, is used as input to the
rule. By doing this, the workflow "understands" that the rule ``pluvial_events`` must run first, before
``sfincs_pre`` is run. In this example, the file name behind ``pluvial_events.output.event_yaml`` is called directly.

An alternative is to only `refer` to a certain input, output or parameter within the workflow, without parsing it
explicitly. This is done with the ``get_ref`` method of the ``Workflow`` class.

.. code-block:: python

    pluvial_events = PluvialDesignEvents(
        precip_nc=get_rainfall.output.precip_nc,
        event_root="data/rainfall/events",
        rps=w.get_ref("$config.rps"),
        wildcard="event",
    )

Here, ``rps`` is an input to ``PluvialDesignEvents`` and it is referred to in the workflow's configuration section
through a special string convention ``$``, in this example ``$config.rps``. If the workflow is parsed to a workflow
file like a Snakemake file, also the config section reference will be given, and not parsed explicitly.

The above example also shows that rules can "expand" or "reduce". This requires a wildcard, which can be
defined as one of the inputs to a rule. The wildcard ``"event"`` is defined in order to define multiple events with
different return periods (see variable ``rps``) which later are expanded in the rule ``sfincs_pre`` (see above) to
prepare precipitation inputs and run the sfincs model.

The coherence between rules with their expand and reductions results in a graph for the workflow.

Methods behind rules
--------------------

You may have seen that there may be many methods and that each method is very specific and requires different inputs.

To know which methods are available and which arguments each methods has (mandatory and optional), you have to
consult the :ref:`API <api>` section, more specifically the part on methods. For instance the
method ``PluvialDesignEvents`` is described under the :ref:`rainfall methods <api_rainfall>`. It shows that it
generates pluvial design events, and that it requires ``precip_nc`` (path to rainfall time series) and ``rps`` (return
periods for which to derive rainfall events) as inputs. Each method is parsed to a ``Method`` instance and from the
arguments, it is defined what the inputs, outputs and parameters of the method should be. Note that in the method API
description, several additional keyword arguments may be provided that are used as additional inputs, and that these
may be described under the method's ``Params``. For instance, you could add ``plot_fig=False`` to the
``PluvialDesignEvents`` instance to suppress plotting of the hyetographs resulting from this method. If you don't,
you'll get a nice graph for free :-).

Storing a workflow file in a HydroFlows ``yaml``
------------------------------------------------
If you want to store the workflow in a ``.yaml`` structure, you can do so with ``w.to_yaml``. You can then read the
yaml back into a workflow with ``Workflow.from_yaml`` in another script.

Creating a workflow file in a selected language
-----------------------------------------------------------------

Even though the workflow can be :ref:`run <run_workflow>` directly from HydroFlows, it is in most cases required
to store the workflow into a typical workflow language such as Snakemake. This is because such languages offer
many additional functionalities to run workflow much more efficiently than HydroFlows. For instance, in Snakemake you
may provide arguments that allow you to allocate certain resources to rules, or balance loads of jobs to several
subprocesses or even nodes on a HPC cluster. This becomes necessary when you wish to compute a large number of
permutations of events (e.g. ensemble forecast, multi-climate, or compound events sets) or simply a very large
event-set (e.g. 1000s of synthetic events).

.. note::

    Currently we only support Snakemake as workflow language. Soon we will also support CWL and we are investigating
    Argo.

.. tab-set::

    .. tab-item:: API

        Writing to snakemake (see example code) can easily be done as follows:

        .. code-block:: python

            w.to_snakemake(f"{w.name}.smk")

    .. tab-item:: CLI

        If you have exported a workflow to a HydroFlows native ``yaml`` file, you can convert it into a Snakemake
        workflow using the `` create`` command. The CLI contains a separate ``--help`` for the ``create`` command.

        .. code-block:: shell

            $ hydroflows create --help

        .. program-output:: hydroflows create --help

        .. code-block:: shell

            $ hydroflows create sfincs_pluvial.yml

Running the python code example yields a file ``sfincs_pluvial.smk`` which contains a Snakemake (default) workflow
which you can then implement in a compute environment of choice. Below you can see the outputs of running the python
workflow script and the ``.smk`` file content that results from it.

.. program-output:: python ../examples/pluvial_hazard.py

.. literalinclude:: ../pluvial_hazard.smk
    :language: yaml

The earlier mentioned wildcards and their expansion and reduction are parsed automatically. The connections between
the rules is organized via their inputs and outputs.

.. _run_workflow:

Running a workflow
------------------
The workflow can be run in your local environment. This does not yield scalability as would be the case if you use
e.g. Snakemake or CWL. This can be useful for instance to test your workflow. Also dry-running is possible to see if
the input-output logic is correct.

.. tab-set::

    .. tab-item:: API

        Dry-running in the API can be done as follows:

        .. code-block:: python

            workflow.run(dryrun=True, tmp="./")

        The workflow will then try to create all the files and you can check the expected activities, wildcard
        expansions and reductions and connections between tasks. The ``tmp`` flag defines in which path the dryrun
        should occur. The file structure will be made relative to this path. Any file will only be a zero-bytes touched
        file.

        Running in the API can be done as follows:

        .. code-block:: python

            workflow.run()

    .. tab-item:: CLI

        .. note::

            Dry running is not yet possible on CLI.

        You may run the workflow directly as follows:

        .. code-block:: shell

            $ hydroflows run sfincs_pluvial.yaml

This will execute all steps in your workflow on your local environment. Naturally make sure that the right Python
environment is activated and that any executables or environment variables you may need are available and specified.
For the building of models, there is a strong reliance on the HydroMT_ model builder. This means that you will need a
HydroMT_ data catalogue that contains the static or dynamic datasets that you want to use in your workflow.

.. _HydroMT: https://deltares.github.io/hydromt
