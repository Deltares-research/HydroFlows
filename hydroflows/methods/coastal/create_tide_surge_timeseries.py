"""Convert waterlevel timeseries into tide and surge timeseries."""

from pathlib import Path
from shutil import copy

import xarray as xr
from pydantic import BaseModel

from hydroflows.methods.method import Method


class Input(BaseModel):
    """Input parameters for the :py:class:`TideSurgeTimeseries` method."""

    waterlevel_timeseries: Path
    """Path to waterlevel timeseries to derive tide and surge from."""


class Output(BaseModel):
    """Output parameters for the :py:class:`TideSurgeTimeseries` method."""

    surge_timeseries: Path
    """Path to output surge timeseries."""

    tide_timeseries: Path
    """Path to output tide timeseries."""


class Params(BaseModel):
    """Params for the :py:class:`TideSurgeTimeseries` method."""

    surge_timeseries: Path = None
    """Path to surge timeseries to use in derivation tide timeseries"""

    tide_timeseries: Path = None
    """Path to tide timeseries to ues in derivation surge timeseries"""


class TideSurgeTimeseries(Method):
    """Method for deriving tide and surge timeseries from waterlevel timeseries.

    If one of or both tide and surge timeseries are passed as params, they are simply copied over to their respective outputs.
    Currently one of tide or surge timeseries params is required.
    Full tidal analysis of a waterlevel timeseries is not yet implemented.

    Utilizes :py:class:`Input <hydroflows.methods.coastal.create_tide_surge_timeseries.Input>`,
    :py:class:`Output <hydroflows.methods.coastal.create_tide_surge_timeseries.Output>`, and
    :py:class:`Params <hydroflows.methods.coastal.create_tide_surge_timeseries.Params>` for method inputs, outputs and params.


    """

    name: str = "create_tide_surge_timeseries"
    input: Input
    output: Output
    params: Params = Params()

    def run(self) -> None:
        """Run TideSurgeTimeseries method."""
        # If both surge and tide timeseries already exist, use those.
        # This is for redundancy. If those timeseries already exist, don't run this method.
        if self.params.surge_timeseries and self.params.tide_timeseries:
            assert (
                self.params.surge_timeseries.exists()
            ), "Provide valid surge timeseries path"
            assert (
                self.params.tide_timeseries.exists()
            ), "Provide valid tide timeseries path"

            copy(self.params.surge_timeseries, self.output.surge_timeseries)
            copy(self.params.tide_timeseries, self.output.tide_timeseries)
        # TODO: make two elif statements nicer. Combine with ternary operators somehow?
        elif self.params.surge_timeseries.exists():
            assert (
                self.params.surge_timeseries.exists()
            ), "Provide valid surge timeseries path"
            copy(self.params.surge_timeseries, self.output.surge_timeseries)

            surge = xr.open_dataarray(self.params.surge_timeseries)
            waterlevel = xr.open_dataarray(self.input.waterlevel_timeseries)

            tide = waterlevel - surge
            tide.to_netcdf(self.output.tide_timeseries)
        elif self.params.tide_timeseries.exists():
            assert (
                self.params.tide_timeseries.exists()
            ), "Provide valid tide timeseries path"
            copy(self.params.tide_timeseries, self.output.tide_timeseries)

            tide = xr.open_dataarray(self.params.tide_timeseries)
            waterlevel = xr.open_dataarray(self.input.waterlevel_timeseries)

            surge = waterlevel - tide
            surge.to_netcdf(self.output.surge_timeseries)
        # TODO: Implement tidal analysis of a single waterlevel timeseries
        else:
            raise NotImplementedError("Tidal analysis not implemented")
