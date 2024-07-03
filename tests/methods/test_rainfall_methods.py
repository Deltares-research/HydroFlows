import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from hydroflows.events import EventSet
from hydroflows.methods import GetERA5Rainfall, PluvialDesignEvents


@pytest.fixture()
def precip_time_series_nc():
    # Generating datetime index
    dates = pd.date_range(start="2000-01-01", end="2009-12-31", freq="h")

    # set a seed for reproducibility
    np.random.seed(0)
    # Generating random rainfall data
    data = np.random.rand(len(dates))

    da = xr.DataArray(
        data,
        dims=("time"),
        coords={"time": dates},
        name="tp",
        attrs={"long_name": "Total precipitation", "units": "mm"},
    )
    return da


def test_pluvial_design_hyeto(precip_time_series_nc, tmp_path):
    # write time series to file
    fn_time_series_nc = Path(tmp_path, "data", "output_scalar.nc")
    os.makedirs(fn_time_series_nc.parent, exist_ok=True)
    precip_time_series_nc.to_netcdf(fn_time_series_nc)

    fn_event_set = Path(tmp_path, "data", "event_set.yml")  # used for assertion
    event_root = fn_event_set.parent
    rps = [1, 10, 100]

    PluvialDesignEvents(
        precip_nc=fn_time_series_nc,
        rps=rps,
        event_root=event_root,
    ).run()
    assert fn_event_set.exists()

    # read data back and check if all event paths are absolute and existing, length is correct
    event_set = EventSet.from_yaml(fn_event_set)
    assert isinstance(event_set.events, list)
    assert len(event_set.events) == len(rps)

    # are all paths absolute
    assert all([Path(event["path"]).is_absolute() for event in event_set.events])
    assert all([Path(event["path"]).exists() for event in event_set.events])

    # test max value is 1
    event = event_set.get_event("p_event01")
    filename = event.forcings[0].path
    fn_csv = fn_time_series_nc.parent / filename
    df = pd.read_csv(fn_csv, parse_dates=True, index_col=0)
    assert df.max().max() == 1.0


def test_get_ERA5_rainfall(sfincs_region_path, tmp_path):
    input = {"sfincs_region": str(sfincs_region_path)}

    fn_time_series = Path(tmp_path, "era5_data.nc")
    output = {"time_series_nc": str(fn_time_series)}

    params = {"start_date": "2000-01-01", "end_date": "2010-12-31"}

    GetERA5Rainfall(input=input, output=output, params=params).run()
    assert fn_time_series.exists()
