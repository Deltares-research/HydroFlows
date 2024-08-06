"""Get return periods from COAST-RP data."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import xarray as xr
from pydantic import BaseModel
from shapely import Point

from hydroflows.methods.method import Method

__all__ = ["GetCoastRP"]


class Input(BaseModel):
    """Input parameters for the :py:class:`GetCoastRP` method."""

    region: Path
    """Path to region geometry file."""

    coastrp_fn: Path
    """Path to full COAST-RP dataset."""


class Output(BaseModel):
    """Output parameters for the :py:class:`GetCoastRP` method."""

    rps_nc: Path
    """Path to return period and values dataset."""


class Params(BaseModel):
    """Params parameters for the :py:class:`GetCoastRP` method."""

    pass


class GetCoastRP(Method):
    """Method for fetching and processing COAST-RP dataset."""

    name: str = "get_coast_rp"

    def __init__(
        self,
        region: Path,
        coastrp_fn: Path,
        data_root: Path = Path("data/input/forcing_data/waterlevel"),
    ) -> None:
        """Create and validate a GetCoastRP instance.

        Parameters
        ----------
        region : Path
            Path to region geometry file.
            Centroid is used to look for closest station to be consistent with GetGTSMData method.
        coastrp_fn : Path
            Path to full COAST-RP dataset.
        data_root : Path, optional
            The folder root where output is stored, by default "data/input/forcing_data/waterlevel"

        See Also
        --------
        :py:class:`Input <hydroflows.methods.coastal.get_coast_rp.Input>`
        :py:class:`Input <hydroflows.methods.coastal.get_coast_rp.Output>`
        :py:class:`Input <hydroflows.methods.coastal.get_coast_rp.Params>`
        """
        self.input: Input = Input(region=region, coastrp_fn=coastrp_fn)
        self.params: Params = Params()

        rps_fn = data_root / "waterlevel_rps.nc"
        self.output: Output = Output(rps_nc=rps_fn)

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
        coast_rp = clip_coastrp(coast_rp, region)
        coast_rp.to_netcdf(self.output.rps_nc)


def clip_coastrp(coast_rp: xr.DataArray, region: gpd.GeoDataFrame) -> xr.DataArray:
    """Clip COAST-RP to given region.

    Parameters
    ----------
    coast_rp : xr.DataArray
        DataArray containing COAST-RP data with lat,lon coords.
    region : gpd.GeoDataFrame
        Region GeoDataFrame

    Returns
    -------
    xr.DataArray
        Clipped COAST-RP DataArray
    """
    points = []
    for station in coast_rp.stations:
        point = Point(
            coast_rp.sel(stations=station).lon.values,
            coast_rp.sel(stations=station).lat.values,
        )
        if region.contains(point)[0]:
            points.append(station)
    return coast_rp.sel(stations=points)
