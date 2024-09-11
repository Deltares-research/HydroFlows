import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from hydroflows.events import EventSet
from hydroflows.methods.rainfall import GetERA5Rainfall, PluvialDesignEvents


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


def test_pluvial_design_hyeto(precip_time_series_nc: xr.DataArray, tmp_path: Path):
    # write time series to file
    fn_time_series_nc = Path(tmp_path, "data", "output_scalar.nc")
    os.makedirs(fn_time_series_nc.parent, exist_ok=True)
    precip_time_series_nc.to_netcdf(fn_time_series_nc)

    rps = [1, 10, 100]
    p_events = PluvialDesignEvents(
        precip_nc=str(fn_time_series_nc),
        event_root=Path(tmp_path, "data"),
        rps=rps,
        ev_type="BM",
        distribution="gev",
    )

    assert len(p_events.params.event_names) == len(rps)

    p_events.run_with_checks()

    # TODO separate this into a new test function?
    # read data back and check if all event paths are absolute and existing, length is correct
    fn_event_set = p_events.output.event_set_yaml
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


def test_get_ERA5_rainfall(sfincs_region_path: Path, tmp_path: Path):
    get_era5 = GetERA5Rainfall(
        region=str(sfincs_region_path),
        data_root=str(tmp_path / "data"),
        filename="era5.nc",
        start_date="2023-11-01",
        end_date="2023-12-31",
    )
    assert get_era5.output.precip_nc == tmp_path / "data" / "era5.nc"
    get_era5.run_with_checks()

    da = xr.open_dataarray(get_era5.output.precip_nc)
    assert da["time"].min() == pd.Timestamp("2023-11-01")
