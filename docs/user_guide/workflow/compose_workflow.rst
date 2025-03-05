.. _compose_workflow:

Compose a workflow
==================

A workflow is basically composed by linking methods together using the output files of one method
as input for another method. To compose a workflow, the following steps are taken:

1. initialize a :term:`workflow` with optional wildcards and configuration.
2. create a workflow :term:`rule` by adding a :term:`method` to the workflow, using the `add_rule` method.

.. figure:: ../../_static/hydroflows_framework_validate.png
    :alt: Compose and validate workflow
    :align: center

Initialize a workflow
---------------------

To initialize the :class:`~hydroflows.workflow.Workflow` class, a user can supply following arguments (all optional):

- The **root directory** *(recommended!)* is the directory where the workflow is executed. All input and output files of the rule are relative to this directory.
- The **workflow configuration** is used to store all workflow parameters and input files which are not output of a rule. Users can add their own parameters to the configuration and use these to initialize the methods. The configuration will also be stored as a separate file in the root directory when parsing the workflow to a workflow engine, see :ref:`parse_to_engine`.
- The **wildcards** are used to evaluate the method wildcards, see :ref:`wildcards`.

.. ipython:: python

    from hydroflows.workflow import Workflow

    # initialize a workflow
    wf = Workflow(
        root="./my_workflow",
        config={"sfincs_exe": "bin/sfincs_v2.1.1/sfincs.exe"},
        wildcards={"region": ["region1", "region2"]},
    )

    # we now have an empty workflow
    wf

Create workflow rules (basic)
-----------------------------

To create a rule based on a method, first the method should be initialized with the required input files and parameters,
then a rule is created by added it to the workflow using the `add_rule` method of the workflow class.

When creating a new rule based on a method the following steps are executed in the background:

- the method :term:`wildcards` are evaluated. This way a method instances for different input files or parameters can be created and executed in parallel.
- the method input files are either linked to the output files of previous rules or set in the workflow configuration.
- a check is performed to ensure the output files are unique (not already used in the workflow).
- the dependencies of the rule are evaluated and the rule is added to the workflow.

.. ipython:: python

    from hydroflows.methods.sfincs import SfincsBuild

    # initialize a new workflow
    wf = Workflow(root="./my_workflow")

    # initialize a method to build a SFINCS model
    sfincs_build = SfincsBuild(
        region="data/region.shp",
        sfincs_root="models/sfincs",
        config="config/hydromt_sfincs.yml",
        catalog_path="data/data_catalog.yml",
    )

    # add the method to the workflow
    wf.add_rule(sfincs_build, rule_id="sfincs_build")

    # we now have a workflow with one rule
    wf


The **output files of the method can be used as input for subsequent methods**, see example below.
Note that the rules need to be created and added to the workflow in the right order to ensure that the output files of one method
are available as input for the next method.

.. ipython:: python

    from hydroflows.methods.rainfall import GetERA5Rainfall

    # initialize a method to get ERA5 rainfall data
    get_rainfall = GetERA5Rainfall(
        region=sfincs_build.output.sfincs_region, # use the output of the previous rule
        start_date="2018-01-01",
        end_date="2018-01-31",
        output_dir="data/rainfall",
    )
    # add the method to the workflow
    wf.add_rule(get_rainfall, rule_id="get_rainfall")

    # we now have a workflow with two rules
    wf

Create workflow rules (repeat wildcards)
----------------------------------------

The same workflow can be created for multiple regions by using :term:`wildcards` in the method input files or parameters.
We use wildcards instead of python loops to ensure that the workflow can be parallelized and executed on a workflow engine.
This is done using the wildcard key between ``{}`` in the input files or parameters of the method, see example below.
Note that the wildcard should be on the input and output to repeat the method for each region,
here that is the ``{region}`` wildcard on the ``region`` input file and the ``sfincs_root`` parameter used to create the output files.
If the wildcard is accidentally only used in the input files or output files, an error will be raised.
The wildcard keys and values should be defined at the workflow level *before* creating the rule.


.. ipython:: python

    # initialize a new workflow with wildcards
    wf = Workflow(root="./my_workflow", wildcards={"region": ["region1", "region2"]})

    # initialize a method to build a SFINCS model
    sfincs_build = SfincsBuild(
        region="data/{region}.geojson",  # use the region wildcard
        sfincs_root="models/sfincs/{region}",
        config="config/hydromt_sfincs.yml",
        catalog_path="data/data_catalog.yml",
    )
    # add the method to the workflow
    wf.add_rule(sfincs_build, rule_id="sfincs_build")

    # inspect the method outputs
    sfincs_build.output

    # initialize a method to get ERA5 rainfall data
    get_rainfall = GetERA5Rainfall(
        region=sfincs_build.output.sfincs_region, # use the output of the previous rule
        start_date="2018-01-01",
        end_date="2018-01-31",
        output_dir="data/rainfall/{region}",
    )
    # add the method to the workflow
    wf.add_rule(get_rainfall, rule_id="get_rainfall")

    # we now have a workflow with two rules which are repeated for region1 and region2
    wf


Create workflow rules (expand and reduce wildcards)
---------------------------------------------------

In order to create multiple output files from a single set of input files (expand) or to create a single output file from multiple input files (reduce),
special methods called ``ExpandMethod`` and ``ReduceMethod`` can be used, see :ref:`expand_reduce_methods`.

For example, the ``PluvialDesignEvents`` method can be used to create multiple events for different return periods from a single rainfall time series.
The method requires a ``wildcard`` parameter to define the wildcard key, while its values will be based on the ``rps`` parameter.
At initialization, an ``ExpandMethod`` stores the key and values as *expand* wildcard which are used to create multiple output files.

.. ipython:: python

    from hydroflows.methods.rainfall import PluvialDesignEvents

    # initialize a new workflow with wildcards
    wf = Workflow(root="./my_workflow")

    # initialize a method to get ERA5 rainfall data
    get_rainfall = GetERA5Rainfall(
        region="data/region.geojson",
        start_date="2018-01-01",
        end_date="2018-01-31",
        output_dir="data/rainfall/{region}",
    )
    # add the method to the workflow
    wf.add_rule(get_rainfall, rule_id="get_rainfall")

    # initialize a method to create pluvial design events
    pluvial_events = PluvialDesignEvents(
        precip_nc=get_rainfall.output.precip_nc,  # use the output of the previous rule
        event_root="data/rainfall/events",
        rps=[2, 5, 10, 50, 100],
        wildcard="event",
    )
    # inspect the method outputs, note the wildcard on the output files
    pluvial_events.output

    # add the method to the workflow
    wf.add_rule(pluvial_events, rule_id="pluvial_events")

    # check if the wildcard is added to the workflow
    wf.wildcards


After an ``ExpandMethod`` is added to the workflow, the wildcard can be used in subsequent rules to repeat the
method for each value of the wildcard value and/or to reduce over multiple input files.
For example, the ``SfincsUpdateForcing``, ``SfincsRun``, and ``SfincsPostprocess`` methods are typically run in parallel for each event
created by the ``PluvialDesignEvents`` method. This is done by adding the `event` wildcard to the input files and parameters
defining the output directories of the methods.
Using a ``ReduceMethod`` the output of the ``SfincsPostprocess`` method can then be reduced to a single output file.
For example, the ``FIATUpdateHazard`` method takes the outputs of all ``SfincsPostprocess`` methods and combines these into a single hazard
dataset as input to Fiat to compoute flood risk.

.. ipython:: python

    from hydroflows.methods.sfincs import SfincsUpdateForcing, SfincsRun, SfincsPostprocess
    from hydroflows.methods.fiat import FIATUpdateHazard

    # Update the sfincs model with all events
    sfincs_update = SfincsUpdateForcing(
        sfincs_inp="models/sfincs/sfincs.inp",  # existing sfincs base model
        event_yaml=pluvial_events.output.event_yaml, # this contains the event wildcard
        output_dir="models/sfincs/simulations",
    )
    wf.add_rule(sfincs_update, rule_id="sfincs_update")

    # Run the sfincs model for all events
    sfincs_run = SfincsRun(
        sfincs_exe="bin/sfincs_v2.1.1/sfincs.exe",
        sfincs_inp=sfincs_update.output.sfincs_out_inp, # this contains the event wildcard
    )
    wf.add_rule(sfincs_run, rule_id="sfincs_run")

    # Postprocess the sfincs model for all events
    sfincs_post = SfincsPostprocess(
        sfincs_map=sfincs_run.output.sfincs_map, # this contains the event wildcard
    )
    wf.add_rule(sfincs_post, rule_id="sfincs_post")

    # Update the hazard model with all events
    fiat_update = FIATUpdateHazard(
        fiat_cfg="models/fiat/fiat.toml", # existing fiat base model
        output_dir="models/fiat/simulations",
        event_set_yaml=pluvial_events.output.event_set_yaml,
        map_type="water_level",
        hazard_maps=sfincs_post.output.sfincs_zsmax, # this contains the event wildcard
        risk=True,
    )
    wf.add_rule(fiat_update, rule_id="fiat_update")

    # we now have a workflow with six rules
    wf

More workflow examples
----------------------

More (complex) examples with full flood risk workflows are available in the HydroFlows :ref:`examples`.
