import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import Point

from hydroflows.methods import WflowBuild, WflowDesignHydro


@pytest.fixture()
def sfincs_src_points():
    return gpd.GeoDataFrame(
        geometry=[
            Point(282937.059, 5079303.114),
        ],
        crs="EPSG:32633",
    )

def test_wflow_build(sfincs_src_points, tmp_path):
    # write region to file
    fn_sfincs_src_points = Path(tmp_path, "data", "sfincs_src_points.geojson")
    os.makedirs(fn_sfincs_src_points.parent, exist_ok=True)
    sfincs_src_points.to_file(fn_sfincs_src_points, driver="GeoJSON")

    input = {
        "sfincs_src_points": str(fn_sfincs_src_points)
    }

    fn_wflow_toml = Path(tmp_path, "model", "wflow.toml")
    output = {
        "wflow_toml": str(fn_wflow_toml)
    }

    WflowBuild(input=input, output=output).run()

    assert fn_wflow_toml.exists()

@pytest.fixture()
def time_series_nc():
    # Generating datetime index
    dates = pd.date_range(start='2000-01-01', end='2009-12-31', freq='D')

    # Generating station IDs
    stations = np.array(['1', '2'], dtype='<U1')

    # Generating random discharge data for each station and date
    data = np.random.rand(len(dates), len(stations)) * 100

    # Creating the DataArray
    discharge_data = xr.DataArray(data,
                                   coords={'time': dates, 'Q_gauges': stations},
                                   dims=['time', 'Q_gauges'],
                                   name='discharge',
                                   attrs={'long_name': 'discharge', 'units': 'm3/s'})

    return discharge_data

def test_wflow_design_hydro(time_series_nc, tmp_path):
    # write time series to file
    fn_time_series_nc = Path(tmp_path, "data", "output_scalar.nc")
    os.makedirs(fn_time_series_nc.parent, exist_ok=True)
    time_series_nc.to_netcdf(fn_time_series_nc)

    input = {
        "time_series_nc": str(fn_time_series_nc)
    }

    fn_design_hydrograph = Path(tmp_path, "model", "design_hydrograph.nc")

    output = {
        "design_hydrograph": str(fn_design_hydrograph)
    }

    WflowDesignHydro(input=input, output=output).run()
    assert fn_design_hydrograph.exists()
