.. _data_methods:

Data pre- and postprocessing methods
====================================

HydroFlows provides a set of data methods for downloading, preprocessing, and postprocessing various data sources.
These methods can be used to retrieve or process coastal, rainfall, climate, flood hazard, raster, and catalog data.

Coastal Data Methods
--------------------
- The :py:class:`~hydroflows.methods.coastal.get_gtsm_data.GetGTSMData` method retrieves water level and tidal time series data from the Global Tide and Surge Model (GTSM).
- The :py:class:`~hydroflows.methods.coastal.coastal_tidal_analysis.CoastalTidalAnalysis` method performs tidal analysis on coastal data to extract the tidal signal from the water level time series.

Rainfall Data Methods
---------------------
- The :py:class:`~hydroflows.methods.rainfall.get_ERA5_rainfall.GetERA5Rainfall` method fetches time series rainfall data from the ERA5 dataset via the `OpenMeteo API <https://open-meteo.com/>`_.

Climate Data Methods
--------------------
- The :py:class:`~hydroflows.methods.climate.climatology.MonthlyClimatology` method derives monthly climatology data from the CMIP6 archive, for climate variables such as temperature and precipitation.
- The :py:class:`~hydroflows.methods.climate.change_factor.ClimateChangeFactors` method calculates climate change factors from monthly climatology for future and present climate conditions.

Flood Hazard Validation Methods
-------------------------------
- The :py:class:`~hydroflows.methods.hazard_validation.floodmarks.FloodmarksValidation` method validates flood hazard data using floodmarks, which are flood depth observations from historical flood events.

Raster Data Methods
-------------------
- The :py:class:`~hydroflows.methods.raster.merge.MergeGriddedDatasets` method merges multiple gridded (raster) datasets into a single dataset using quantile reduction. It can be used to combine different datasets such as climatology datasets from different climate models.

Catalog Data Methods
--------------------
- The :py:class:`~hydroflows.methods.catalog.merge_catalogs.MergeCatalogs` method merges multiple data catalogs into a single catalog. It is useful to combine outputs from methods which generate data catalogs and are input to other methods.

Additional Methods
------------------
- The :py:class:`~hydroflows.methods.script.script_method.ScriptMethod` method allows running a simple script without validation of the input, output, or parameters. It provides flexibility for custom data processing tasks.
