"""Get ERA5 rainfall method."""

from datetime import datetime
from pathlib import Path

import geopandas as gpd
import xarray as xr
from pydantic import BaseModel, FilePath

from hydroflows.methods.method import Method
from hydroflows.methods.rainfall.functions import get_era5_open_meteo


class Input(BaseModel):
    """Input parameters."""

    sfincs_region: FilePath

class Output(BaseModel):
    """Output parameters."""

    time_series_nc: Path

class Params(BaseModel):
    """Parameters."""

    start_date: datetime
    end_date: datetime

class GetERA5Rainfall(Method):
    """Rule for getting ERA5 rainfall at the centroid of a polygon region."""

    name: str = "get_ERA5_rainfall"
    params: Params
    input: Input
    output: Output

    def run(self):
        """Run the GetERA5Rainfall method."""
        # read the region polygon file
        gdf = gpd.read_file(self.input.sfincs_region)
        # define the target coordinate reference system as EPSG 4326
        tgt_crs = 'EPSG:4326'
        # reproject the GeoDataFrame to the target CRS
        gdf = gdf.to_crs(tgt_crs)
        # Calculate the centroid of each polygon
        centroid = gdf.geometry.centroid
        # Extract latitude and longitude coordinates from the centroid geometries
        centroid_lon = centroid.x.values[0]
        centroid_lat = centroid.y.values[0]
        # get the data as df
        df = get_era5_open_meteo(
            lat=centroid_lat,
            lon=centroid_lon,
            start_date=self.params.start_date,
            end_date=self.params.end_date,
            variables="precipitation")
        # convert df to xarray ds
        ds = xr.Dataset.from_dataframe(df)
        # save ds
        ds.to_netcdf(self.output.time_series_nc)
