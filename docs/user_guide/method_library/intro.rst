.. _method_library:

Method library
==============


Flood risk workflows
--------------------


HydroFlows provides a modular set of methods for flood risk analysis. These methods are designed to be compatible with each other, allowing seamless integration into typical
flood risk workflows. These methods can be categorized into two main groups:

1. **Data Methods** (orange blocks in Figure) - Handle data retrieval and postprocessing for coastal, rainfall, and discharge data, but also visualization (not included in the figure).
2. **Model-Related Methods** (yellow and green blocks in Figure) - Building (model setup methods; yellow blocks), updating, running, and postprocessing (model methods; green blocks) of the supported models (i.e., SFINCS, Wflow, Delft-FIAT, FloodAdapt).

.. figure:: ../../_static/hydroflows_workflows.svg
    :alt: HydroFlows Workflows
    :align: center

Data Methods
------------
The data methods in HydroFlows include both preprocessing methods like data retrieval from external sources, such as ERA5 and GTSM, and postprocessing methods for further analysis.
The postprocessing methods allow users to derive design events for coastal, rainfall, and discharge data using methods like :py:class:`~hydroflows.methods.coastal.coastal_design_events.CoastalDesignEvents`
, :py:class:`~hydroflows.methods.rainfall.pluvial_design_events.PluvialDesignEvents` , and :py:class:`~hydroflows.methods.discharge.fluvial_design_events.FluvialDesignEvents`.
Getting rainfall design events from the global `GPEX <https://www.sciencedirect.com/science/article/pii/S0022169423005000>`_ Intensity-Duration-Frequency (IDF)
curve data is also supported with the :py:class:`~hydroflows.methods.rainfall.pluvial_design_events_GPEX.PluvialDesignEventsGPEX` method.

Additionally, historical events can be extracted from time series data using the ``HistoricalEvents`` method,
while the impact of future climate conditions on existing coastal and rainfall timeseries can be estimated with the :py:class:`~hydroflows.methods.coastal.future_slr.FutureSLR`
and :py:class:`~hydroflows.methods.rainfall.future_climate_rainfall.FutureClimateRainfall` methods,
respectivelly. Finally, in the postprocessing methods, the user can validate (and visualize) a flood hzard map against floodmarks
(:py:class:`~hydroflows.methods.hazard_validation.floodmarks.FloodmarksValidation` method; not included in the figure).

An example on how a user can combine these methods is by retrieving GTSM data for an area using the :py:class:`~hydroflows.methods.coastal.get_gtsm_data.GetGTSMData` method and
then deriving coastal design events for the same area using :py:class:`~hydroflows.methods.coastal.coastal_design_events.CoastalDesignEvents`
(see the `coastal_event` notebook). Similarly, ERA5 precipitation data can be downloaded with the :py:class:`~hydroflows.methods.rainfall.get_ERA5_rainfall.GetERA5Rainfall` method and
used to generate rainfall design events with :py:class:`~hydroflows.methods.rainfall.pluvial_design_events.PluvialDesignEvents`. Users also have the option to provide their own time series data in the required
format for use in the event methods.

The event methods can be used to generate event sets that serve as inputs for the hazard model (SFINCS),
which can be updated using the :py:class:`~hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing` method, as described in the model-related methods below.

An overview with the current supported data methods in HydroFlows is shown in the table below.

.. list-table:: Table overview with the available data methods
    :header-rows: 1
    :widths: 30 35 35

    * - Data Type
      - Pre-Process Data Methods
      - Post-Process/Event Methods
    * - Coastal data
      - :py:class:`~hydroflows.methods.coastal.get_gtsm_data.GetGTSMData`
      - :py:class:`~hydroflows.methods.coastal.coastal_tidal_analysis.CoastalTidalAnalysis`
        :py:class:`~hydroflows.methods.coastal.coastal_design_events.CoastalDesignEvents`
        :py:class:`~hydroflows.methods.coastal.coastal_design_events_from_rp_data.CoastalDesignEventFromRPData`
        :py:class:`~hydroflows.methods.coastal.future_slr.FutureSLR`
        CoastalHistoricalEvents
    * - Rainfall data
      - :py:class:`~hydroflows.methods.rainfall.get_ERA5_rainfall.GetERA5Rainfall`
      - :py:class:`~hydroflows.methods.rainfall.pluvial_design_events.PluvialDesignEvents`
        :py:class:`~hydroflows.methods.rainfall.pluvial_design_events_GPEX.PluvialDesignEventsGPEX`
        :py:class:`~hydroflows.methods.rainfall.future_climate_rainfall.FutureClimateRainfall`
        PluvialHistoricalEvents
    * - Discharge data
      - N.A.
      - :py:class:`~hydroflows.methods.discharge.fluvial_design_events.FluvialDesignEvents`
        FluvialHistoricalEvents
    * - Validation/Visualization
      - N.A.
      - :py:class:`~hydroflows.methods.hazard_validation.floodmarks.FloodmarksValidation`


Model-Related Methods
---------------------

The model-related methods are designed for building, updating, running, and postprocessing supported models.
These methods are divided into two categories: model setup methods (yellow blocks in the figure) and general model methods for updating,
running, and postprocessing built models (green blocks in the figure).

This separation enables a more modular approach, as model setup methods require a configuration file,
whereas the remaining model methods do not. This flexibility allows users to incorporate different data sources
(global or local) or adjust model setup settings while keeping the updating, running, and postprocessing steps unchanged.

The model setup methods include the :py:class:`~hydroflows.methods.sfincs.sfincs_build.SfincsBuild`
, :py:class:`~hydroflows.methods.wflow.wflow_build.WflowBuild`, :py:class:`~hydroflows.methods.fiat.fiat_build.FIATBuild` and
:py:class:`~hydroflows.methods.flood_adapt.setup_flood_adapt.SetupFloodAdapt` methods for setting up the SFINCS, Wflow, Delft-FIAT and FloodAdapt models, respectively.
The model setup methods require an Area of Interest (AOI), a data catalog, and a HydroMT configuration file as input.
The user should always start by setting up the SFINCS model. A coupling between the
models is achieved since the :py:class:`~hydroflows.methods.sfincs.sfincs_build.SfincsBuild` outputs can be used as input for the :py:class:`~hydroflows.methods.fiat.fiat_build.FIATBuild` and
:py:class:`~hydroflows.methods.wflow.wflow_build.WflowBuild` methods (see for example the `pluvial_fluvial_risk` notebook example).

The general model methods include the updating, running, and postprocessing methods for SFINCS, FIAT and Wflow models.

If a user wants to derive a discharge boundary for the hazard model using Wflow and has already built a coupled Wflow-to-SFINCS model,
the Wflow forcings can be updated using the :py:class:`~hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing` method.
The updated model can then be executed with the :py:class:`~hydroflows.methods.wflow.wflow_run.WflowRun` method,
and the final output can be postprocessed using the :py:class:`~hydroflows.methods.discharge.fluvial_design_events.FluvialDesignEvents` method.
This will generate an event catalog compatible with the :py:class:`~hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing` method.

For Sfincs, the user can update the model with the event sets derived from the data methods (pluvial, fluvial or coastal forcings)
using the :py:class:`~hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing` method,
run the model with the :py:class:`~hydroflows.methods.sfincs.sfincs_run.SfincsRun` method, and postprocess the model output with the :py:class:`~hydroflows.methods.sfincs.sfincs_postprocess.SfincsPostprocess`
and :py:class:`~hydroflows.methods.sfincs.sfincs_downscale.SfincsDownscale` methods (see for example the `pluvial_hazard` notebook example)

For FIAT, the user can update the model with the postprocessed hazard maps derived from the :py:class:`~hydroflows.methods.sfincs.sfincs_postprocess.SfincsPostprocess`
using the :py:class:`~hydroflows.methods.fiat.fiat_update.FIATUpdateHazard` method, run the model with the :py:class:`~hydroflows.methods.fiat.fiat_run.FIATRun` method,
and postprocess the model output with the FIATVisualize method (in development; see for example the `pluvial_risk` notebook example).

A FloodAdapt database can be created using the HydroFlows event set definition with
the :py:class:`~hydroflows.methods.flood_adapt.setup_flood_adapt.SetupFloodAdapt` method.

For more information on how to combine these methods for flood risk analysis using HydroFlows, refer to the examples section for typical workflows.

An overview with the current supported model-related methods in HydroFlows is shown in the table below.

.. list-table:: Table overview with methods
    :header-rows: 1
    :widths: 40 15 40 10 50

    * -
      - build model
      - update model
      - run model
      - postprocess model output
    * - SFINCS (flood hazard)
      - :py:class:`~hydroflows.methods.sfincs.sfincs_build.SfincsBuild` :py:class:`~hydroflows.methods.sfincs.sfincs_region.SfincsRegion`
      - :py:class:`~hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing`
      - :py:class:`~hydroflows.methods.sfincs.sfincs_run.SfincsRun`
      - :py:class:`~hydroflows.methods.hazard_validation.floodmarks.FloodmarksValidation` :py:class:`~hydroflows.methods.sfincs.sfincs_downscale.SfincsDownscale` :py:class:`~hydroflows.methods.sfincs.sfincs_postprocess.SfincsPostprocess`
    * - Wflow (discharge boundary)
      - :py:class:`~hydroflows.methods.wflow.wflow_build.WflowBuild`
      - :py:class:`~hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing` WflowDownscale ClimateChangeFactors
      - :py:class:`~hydroflows.methods.wflow.wflow_run.WflowRun`
      - (see Data Methods)
    * - Delft-FIAT (impact)
      - :py:class:`~hydroflows.methods.fiat.fiat_build.FIATBuild`
      - :py:class:`~hydroflows.methods.fiat.fiat_update.FIATUpdateHazard`
      - :py:class:`~hydroflows.methods.fiat.fiat_run.FIATRun`
      - FIATVisualize
    * - FloodAdapt
      - :py:class:`~hydroflows.methods.flood_adapt.setup_flood_adapt.SetupFloodAdapt`
      - N.A.
      - N.A.
      - N.A.

In addition to the methods listed above, the following methods are available: :py:class:`~hydroflows.methods.script.script_method.ScriptMethod` method to run a simple script (not including validatation of the input, outpur, or parameters),
and :py:class:`~hydroflows.methods.catalog.merge_catalogs.MergeCatalogs` method for merging multiple data catalogs into a single catalog.
