"""Get ERA5 rainfall method."""

from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import xarray as xr
from pydantic import BaseModel

from hydroflows.methods.method import Method


class Input(BaseModel):
    """Input parameters for the :py:class:`GetERA5Rainfall` method."""

    region: Path
    """
    The file path to the geometry file for which we want
    to download ERA5 rainfall time series at its centroid.
    An example of such a file could be the SFINCS region GeoJSON.
    """


class Output(BaseModel):
    """Output parameters for the :py:class:`GetERA5Rainfall` method."""

    precip_nc: Path
    """The path to the NetCDF file with the derived ERA5 rainfall timeseries."""


class Params(BaseModel):
    """Parameters for the :py:class:`GetERA5Rainfall`."""

    data_input_root: Path
    """The root folder where the data is stored."""

    start_date: datetime = datetime(1990, 1, 1)
    """The start date for downloading the ERA5 precipitation time series."""

    end_date: datetime = datetime(2023, 12, 31)
    """The end date for downloading the ERA5 precipitation time series."""


class GetERA5Rainfall(Method):
    """Rule for downloading ERA5 rainfall data at the centroid of a region."""

    name: str = "get_ERA5_rainfall"

    def __init__(self, region: Path, data_input_root: Path = "data/input", **params):
        """Create and validate a GetERA5Rainfall instance.

        Parameters
        ----------
        region : Path
            The file path to the geometry file for which we want
            to download ERA5 rainfall time series at its centroid.
        data_input_root : Path, optional
            The root folder where the data is stored, by default "data/input".
        **params
            Additional parameters to pass to the GetERA5Rainfall instance.

        See Also
        --------
        :py:class:`GetERA5Rainfall Input <hydroflows.methods.rainfall.get_ERA5_rainfall.Input>`
        :py:class:`GetERA5Rainfall Output <hydroflows.methods.rainfall.get_ERA5_rainfall.Output>`
        :py:class:`GetERA5Rainfall Params <hydroflows.methods.rainfall.get_ERA5_rainfall.Params>`
        """
        self.params: Params = Params(data_input_root=data_input_root, **params)
        self.input: Input = Input(region=region)

        precip_nc = Path(self.params.data_input_root) / "era5_precip.nc"
        self.output: Output = Output(precip_nc=precip_nc)

    def run(self):
        """Run the GetERA5Rainfall method."""
        # check if the input files and the output directory exist
        self.check_input_output_paths()

        # read the region polygon file
        gdf: gpd.GeoDataFrame = gpd.read_file(self.input.region).to_crs("EPSG:4326")
        # Calculate the centroid of each polygon
        centroid = gdf.geometry.centroid

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
        print(f"Request failed with status code {response.status_code}")
        return None
