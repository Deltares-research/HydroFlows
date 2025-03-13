.. _model_methods:

Model Methods
=============

The model methods are designed for building, updating, running, and postprocessing supported models.
An overview with the current supported model-related methods in HydroFlows is shown in the table below.

Model build methods
-------------------
The model setup methods require an Area of Interest (AOI), a data catalog, and a HydroMT configuration file as input.
Through this configuration file, a user can incorporate different data sources (global or local) or adjust model setup settings.
For a flood model chain, a user should start by setting up the SFINCS model which determines where input boundary data is needed
from e.g. the Wflow model and for which area the impact model (Delft-FIAT) should be build.
A coupling between the models is achieved since the :py:class:`~hydroflows.methods.sfincs.sfincs_build.SfincsBuild` outputs can be
used as input for the :py:class:`~hydroflows.methods.fiat.fiat_build.FIATBuild` (through the ``sfincs_subgrid_dep`` file) and
:py:class:`~hydroflows.methods.wflow.wflow_build.WflowBuild` (through the ``sfincs_src_points``) methods.
See the pluvial and fluvial flood risk :ref:`examples` for more details.

A FloodAdapt database can be created from SFINCS and Delft-FIAT models and a ``EventSet`` definition with
the :py:class:`~hydroflows.methods.flood_adapt.setup_flood_adapt.SetupFloodAdapt` method.

Model update methods
-------------------
Once a model is built, the user can update the model with forcing data.
The **Wflow** model is typically updated with multiple years of meteorological data to derive long time series of discharge.
The meteorological forcing of the Wflow model can be scaled using gridded monthly climate change factors
For flood hazard analysis these are used as input to (statistical) methods to derive (desing) events for hydrodynamic models.
The **SFINCS** model is updated with hydro-meteorological (pluvial, fluvial, coastal) event data,
see the :ref:`event_methods` section for more details.
The **Delft-FIAT model** is updated with postprocessed hazard maps derived from the SFINCS model.
For flood risk analysis it also requires an EventSet file as input, where individual events have return periods defined.

Model run methods
-----------------
The model run methods are used to run the model with the updated forcing data.
For all models, the ``run_method`` parameter can be use to specify if the model should be run with an executable, or docker container.


Model postprocess methods
-------------------------
The model postprocess methods are used to visualize the model results or transform the model output to a different format.


.. list-table:: Table overview with model-related methods
    :header-rows: 1
    :widths: 40 15 40 10 50

    * - Model
      - build model
      - update model
      - run model
      - postprocess model
    * - SFINCS (flood hazard)
      - :py:class:`~hydroflows.methods.sfincs.sfincs_build.SfincsBuild`
        :py:class:`~hydroflows.methods.sfincs.sfincs_region.SfincsRegion`
      - :py:class:`~hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing`
      - :py:class:`~hydroflows.methods.sfincs.sfincs_run.SfincsRun`
      - :py:class:`~hydroflows.methods.sfincs.sfincs_downscale.SfincsDownscale`
        :py:class:`~hydroflows.methods.sfincs.sfincs_postprocess.SfincsPostprocess`
    * - Wflow (discharge boundary)
      - :py:class:`~hydroflows.methods.wflow.wflow_build.WflowBuild`
      - :py:class:`~hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing`
        :py:class:`~hydroflows.methods.wflow.wflow_update_factors.WflowUpdateFactors`
      - :py:class:`~hydroflows.methods.wflow.wflow_run.WflowRun`
      - N.A.
    * - Delft-FIAT (impact)
      - :py:class:`~hydroflows.methods.fiat.fiat_build.FIATBuild`
      - :py:class:`~hydroflows.methods.fiat.fiat_update.FIATUpdateHazard`
      - :py:class:`~hydroflows.methods.fiat.fiat_run.FIATRun`
      - :py:class:`~hydroflows.methods.fiat.fiat_visualize.FIATVisualize`
    * - FloodAdapt
      - :py:class:`~hydroflows.methods.flood_adapt.setup_flood_adapt.SetupFloodAdapt`
      - N.A.
      - N.A.
      - N.A.
