"""Get return periods from COAST-RP data."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import xarray as xr
from pydantic import BaseModel

from hydroflows.methods.method import Method


class Input(BaseModel):
    """Input parameters for the :py:class:`GetCoastRP` method."""

    region: Path
    """Path to region geometry file."""

    coastrp_fn: Path
    """Path to COAST-RP dataset."""


class Output(BaseModel):
    """Output parameters for the :py:class:`GetCoastRP` method."""

    rps_nc: Path
    """Path to return period and values dataset."""


class Params(BaseModel):
    """Params parameters for the :py:class:`GetCoastRP` method."""

    pass


class GetCoastRP(Method):
    """Method for fetching and processing COAST-RP dataset.

    Utilizes :py:class:`Input <hydroflows.methods.coastal.get_coast_rp.Input>`,
    :py:class:`Output <hydroflows.methods.coastal.get_coast_rp.Output>`, and
    :py:class:`Params <hydroflows.methods.coastal.get_coast_rp.Params>` for method inputs, outputs and params.

    """

    name: str = "get_coast_rp"
    input: Input
    output: Output
    params: Params = Params()

    def run(self) -> None:
        """Run GetCoastRP Method."""
        region = gpd.read_file(self.input.region)
        coast_rp = xr.open_dataset(self.input.coastrp_fn).rename(
            {
                "station_x_coordinate": "lon",
                "station_y_coordinate": "lat",
            }
        )
        coast_rp = xr.concat(
            [coast_rp[var] for var in coast_rp.data_vars if var != "station_id"],
            dim=pd.Index([1, 2, 5, 10, 25, 50, 100, 250, 500, 1000], name="rps"),
        ).to_dataset(name="return_values")
        dist = (coast_rp.lat - region.centroid.y.values) ** 2 + (
            coast_rp.lon - region.centroid.x.values
        ) ** 2
        coast_rp = coast_rp.isel(dist.argmin().values)

        coast_rp.to_netcdf(self.output.rps_nc)
