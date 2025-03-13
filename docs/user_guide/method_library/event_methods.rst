.. _event_methods:

Historical, future and design event methods
===========================================


Model events and EventSets
--------------------------

The model :class:`~hydroflows.events.Event` class defines fluvial (discharge), pluvial (rainfall), or coastal (water levels) forcings.
The class contains one or more :class:`hydroflows.events.Forcing` objects with references to time series data, the start and end times
of the event, and optionally a return period (RP) associated with the event.

The :class:`~hydroflows.events.EventSet` class is a collection of references to multiple `Event` files.
It is used to group the events which are jointly used to e.g. calculate risk.

All event methods generate one or more `Event` files and one `EventSet` file.
The `Event` files serve as inputs for the hazard model (SFINCS) using the
:py:class:`~hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing` method.

The `EventSet` file is used as input to the risk model (FIAT) using the :py:class:`~hydroflows.methods.fiat.fiat_update.FIATUpdateHazard` method
and flood adaptation model (FloodAdapt) using the :py:class:`~hydroflows.methods.flood_adapt.setup_flood_adapt.SetupFloodAdapt` method.


Event methods
-------------

HydroFlows has several methods to generate events for historical, future, and design events.

The historical events can be extracted from time series data using the :py:class:`~hydroflows.methods.historical_events.historical_events.HistoricalEvents` method and contain one or more forcings.

Design events are currently univariate and are derived using extreme value analysis from time series data.
The design events can be derived for coastal (storm tide), rainfall, and discharge time series data.
For coastal design events, a second method is available to use existing return period `CoastRP <https://data.4tu.nl/articles/dataset/COAST-RP_A_global_COastal_dAtaset_of_Storm_Tide_Return_Periods/13392314>`_ dataset.
For rainfall design events, the global `GPEX <https://www.sciencedirect.com/science/article/pii/S0022169423005000>`_ Intensity-Duration-Frequency (IDF) curve data can be used.

The future climate events are used to scale historical or design events to future climate conditions.
For rainfall the multiplicative Clausius-Clapeyron scaling is used, while for sea level rise an additive approach is used.
For discharge events, rather than scaling then scaling the events a new set of events is generated from hydrological simulations under future climate conditions by scaling the input meteorological data, see the *data method* :py:class:`~hydroflows.methods.climate.change_factor.ChangeFactor`.

An overview with the current supported event methods in HydroFlows is shown in the table below.

.. list-table:: Table overview with the available event methods
    :header-rows: 1
    :widths: 16 28 28 28

    * - Event Type
      - Historical
      - Design events
      - Future climate events
    * - Coastal
      - :py:class:`~hydroflows.methods.historical_events.historical_events.HistoricalEvents`
      - :py:class:`~hydroflows.methods.coastal.coastal_design_events.CoastalDesignEvents` :py:class:`~hydroflows.methods.coastal.coastal_design_events_from_rp_data.CoastalDesignEventFromRPData`
      - :py:class:`~hydroflows.methods.coastal.future_slr.FutureSLR`
    * - Rainfall
      - :py:class:`~hydroflows.methods.historical_events.historical_events.HistoricalEvents`
      - :py:class:`~hydroflows.methods.rainfall.pluvial_design_events.PluvialDesignEvents` :py:class:`~hydroflows.methods.rainfall.pluvial_design_events_GPEX.PluvialDesignEventsGPEX`
      - :py:class:`~hydroflows.methods.rainfall.future_climate_rainfall.FutureClimateRainfall`
    * - Discharge
      - :py:class:`~hydroflows.methods.historical_events.historical_events.HistoricalEvents`
      - :py:class:`~hydroflows.methods.discharge.fluvial_design_events.FluvialDesignEvents`
      - N.A.
    * - Combined
      - :py:class:`~hydroflows.methods.historical_events.historical_events.HistoricalEvents`
      - N.A.
      - N.A.
