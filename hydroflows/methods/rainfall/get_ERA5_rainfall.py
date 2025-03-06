"""Get ERA5 rainfall method."""

import logging
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import xarray as xr

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

logger = logging.getLogger(__name__)


class Input(Parameters):
    """Input parameters for the :py:class:`GetERA5Rainfall` method."""

    region: Path
    """
    The file path to the geometry file for which we want
    to download ERA5 rainfall time series at its centroid.
    An example of such a file could be the SFINCS region GeoJSON.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`GetERA5Rainfall` method."""

    precip_nc: Path
    """The path to the NetCDF file with the derived ERA5 rainfall timeseries."""


class Params(Parameters):
    """Parameters for the :py:class:`GetERA5Rainfall`."""

    output_dir: Path = Path("data/input")
    """The root folder where the data is stored."""

    filename: str = "era5_precip.nc"
    """The filename for the ERA5 precipitation time series."""

    start_date: datetime = datetime(1990, 1, 1)
    """The start date for downloading the ERA5 precipitation time series."""

    end_date: datetime = datetime(2023, 12, 31)
    """The end date for downloading the ERA5 precipitation time series."""


class GetERA5Rainfall(Method):
    """Rule for downloading ERA5 rainfall data at the centroid of a region."""

    name: str = "get_ERA5_rainfall"

    _test_kwargs = {
        "region": Path("region.geojson"),
    }

    def __init__(self, region: Path, output_dir: Path = "data/input", **params):
        """Create and validate a GetERA5Rainfall instance.

        Parameters
        ----------
        region : Path
            The file path to the geometry file for which we want
            to download ERA5 rainfall time series at its centroid.
        output_dir : Path, optional
            The root folder where the data is stored, by default "data/input".
        **params
            Additional parameters to pass to the GetERA5Rainfall instance.

        See Also
        --------
        :py:class:`GetERA5Rainfall Input <hydroflows.methods.rainfall.get_ERA5_rainfall.Input>`
        :py:class:`GetERA5Rainfall Output <hydroflows.methods.rainfall.get_ERA5_rainfall.Output>`
        :py:class:`GetERA5Rainfall Params <hydroflows.methods.rainfall.get_ERA5_rainfall.Params>`
        """
        self.params: Params = Params(output_dir=output_dir, **params)
        self.input: Input = Input(region=region)
        self.output: Output = Output(
            precip_nc=self.params.output_dir / self.params.filename
        )

    def _run(self):
        """Run the GetERA5Rainfall method."""
        # read the region polygon file
        gdf: gpd.GeoDataFrame = gpd.read_file(self.input.region)
        # Calculate the centroid of each polygon
        centroid = gdf.geometry.centroid.to_crs("EPSG:4326")

        # get the data as df
        df = get_era5_open_meteo(
            lat=centroid.y.values[0],
            lon=centroid.x.values[0],
            start_date=self.params.start_date,
            end_date=self.params.end_date,
            variables="precipitation",
        )
        # convert df to xarray ds
        ds = xr.Dataset.from_dataframe(df)
        # save ds
        ds.to_netcdf(self.output.precip_nc)


def get_era5_open_meteo(lat, lon, start_date: datetime, end_date: datetime, variables):
    """Return ERA5 rainfall.

    Return a df with ERA5 raifall data at specific point location.
    using an API

    Parameters
    ----------
    lat : (float)
        Latitude coordinate.
    lon : (float)
        Longitude coordinate.
    start_date : (str)
        Start date for data download
    end_date : (str)
        End date for data download
    variables : (str)
        Variable to download
    """
    base_url = r"https://archive-api.open-meteo.com/v1/archive"
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    url = (
        f"{base_url}?latitude={lat}&longitude={lon}"
        f"&start_date={start_date_str}&end_date={end_date_str}"
        f"&hourly={variables}"
    )
    response = requests.get(url)

    # Check if request was successful
    if response.status_code == 200:
        # Parse response as JSON
        data = response.json()
        # make a df
        df = pd.DataFrame(data["hourly"]).set_index("time")
        df.index = pd.to_datetime(df.index)
        return df
    else:
        # If request failed, return None
        logging.info("Request failed with status code %s", response.status_code)
        return None
