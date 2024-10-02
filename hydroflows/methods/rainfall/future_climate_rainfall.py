"""Future climate rainfall method."""

from pathlib import Path

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


class Input(Parameters):
    """Input parameters for the :py:class:`FutureClimateRainfall` method."""

    precip_nc: Path
    """
    The file path to the rainfall time series in NetCDF format which are used
    to derive the historical events of interest. This file should contain a time dimension
    This time series can be derived either by the
    :py:class:`hydroflows.methods.rainfall.get_ERA5_rainfall.GetERA5Rainfall`
    or can be directly supplied by the user.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`FutureClimateRainfall` method."""


class FutureClimateRainfall(Method):
    """Rule for deriving future climate rainfall by upscaling a event."""

    name: str = "future_climate_rainfall"
