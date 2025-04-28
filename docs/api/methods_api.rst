.. currentmodule:: hydroflows.methods

Predefined methods
==================

Model methods
-------------

These methods are used to build, preprocess, run and postprocess models.
Currently the SFINCS hydrodynamic model, Wflow hydrological model, Delft-FIAT flood impact model are supported.

.. autosummary::
   :toctree: ../_generated
   :template: module-template.rst

   fiat.fiat_build
   fiat.fiat_update
   fiat.fiat_run
   fiat.fiat_visualize
   sfincs.sfincs_region
   sfincs.sfincs_build
   sfincs.sfincs_update_forcing
   sfincs.sfincs_run
   sfincs.sfincs_downscale
   sfincs.sfincs_postprocess
   wflow.wflow_build
   wflow.wflow_update_forcing
   wflow.wflow_update_factors
   wflow.wflow_run
   flood_adapt.setup_flood_adapt
   flood_adapt.prep_sfincs_models

Historical, future and design event methods
-------------------------------------------

These methods are used to generate :class:`~hydroflows.methods.events.Event` and :class:`~hydroflows.methods.events.Eventset` data
which are used as input for the hydrodynamic and impact models.

.. autosummary::
   :toctree: ../_generated
   :template: module-template.rst

   coastal.coastal_design_events_from_rp_data
   coastal.coastal_design_events
   coastal.future_slr
   discharge.fluvial_design_events
   historical_events.historical_events
   rainfall.future_climate_rainfall
   rainfall.pluvial_design_events
   rainfall.pluvial_design_events_GPEX

Data pre- and postprocessing methods
------------------------------------

These methods are used to download, preprocess or postprocess various data sources.

.. autosummary::
   :toctree: ../_generated
   :template: module-template.rst

   catalog.merge_catalogs
   climate.climatology
   climate.change_factor
   coastal.coastal_tidal_analysis
   coastal.get_coast_rp
   coastal.get_gtsm_data
   hazard_validation.floodmarks
   rainfall.get_ERA5_rainfall
   raster.merge

Python script methods
---------------------

Python scripts can directly be added to a workflow using the `ScriptMethod` class.
For usage and limitations see :ref:`python_script`.

.. autosummary::
   :toctree: ../_generated
   :template: module-template.rst

   script.script_method

Dummy methods
-------------

These methods are used for documentation and testing purposes only.

.. autosummary::
   :toctree: ../_generated
   :template: module-template.rst

   dummy.combine_dummy_events
   dummy.postprocess_dummy_event
   dummy.prepare_dummy_events
   dummy.run_dummy_event
