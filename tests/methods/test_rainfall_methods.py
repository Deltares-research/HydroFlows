import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from hydroflows.methods import GetERA5Rainfall, PluvialDesignHyeto


@pytest.fixture()
def precip_time_series_nc():
    # Generating datetime index
    dates = pd.date_range(start='2000-01-01', end='2009-12-31', freq='h')

    # set a seed for reproducibility
    np.random.seed(0)
    # Generating random rainfall data
    data = np.random.rand(len(dates))

    da = xr.DataArray(
        data,
        dims=('time'),
        coords={'time': dates},
        name='tp',
        attrs={'long_name': 'Total precipitation', 'units': 'mm'}
    )
    return da

def test_pluvial_design_hyeto(precip_time_series_nc, tmp_path):
    # write time series to file
    fn_time_series_nc = Path(tmp_path, "data", "output_scalar.nc")
    os.makedirs(fn_time_series_nc.parent, exist_ok=True)
    precip_time_series_nc.to_netcdf(fn_time_series_nc)

    input = {
        "time_series_nc": str(fn_time_series_nc)
    }

    fn_data_catalog = Path(tmp_path, "data", "catalog.yml")

    output = {
        "event_catalog": str(fn_data_catalog)
    }

    PluvialDesignHyeto(input=input, output=output).run()
    assert fn_data_catalog.exists()

def test_get_ERA5_rainfall(sfincs_region_path, tmp_path):
    input = {"sfincs_region": str(sfincs_region_path)}

    fn_time_series = Path(tmp_path, "era5_data.nc")
    output = {"time_series_nc": str(fn_time_series)}

    params = {
        "start_date": "2000-01-01",
        "end_date": "2010-12-31"
    }

    GetERA5Rainfall(input=input, output=output, params=params).run()
    assert fn_time_series.exists()
