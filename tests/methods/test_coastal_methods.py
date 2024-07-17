from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from hydroflows.methods import (
    CoastalDesignEvents,
    GetCoastRP,
    GetGTSMData,
    GetWaterlevelRPS,
    TideSurgeTimeseries,
)


@pytest.fixture()
def waterlevel_timeseries():
    dates = pd.date_range(start="2000-01-01", end="2015-12-31", freq="10min")

    np.random.seed(1234)
    data = np.random.rand(len(dates))

    da = xr.DataArray(
        data=data,
        dims=("time"),
        coords={"time": dates},
        name="h",
    )

    return da


@pytest.fixture()
def tide_surge_timeseries():
    dates = pd.date_range(start="2000-01-01", end="2015-12-31", freq="10min")

    np.random.seed(1234)
    data1 = np.random.rand(len(dates))
    np.random.seed(5678)
    data2 = np.random.rand(len(dates))

    t = xr.DataArray(data=data1, dims=("time"), coords={"time": dates}, name="t")
    s = xr.DataArray(data=data2, dims=("time"), coords={"time": dates}, name="s")

    return t, s


@pytest.fixture()
def rps_nc():
    rps = xr.Dataset(
        coords=dict(rps=("rps", [1, 10, 100])),
        data_vars=dict(return_values=(["rps"], np.array([0.5, 1, 1.5]))),
    )

    return rps


def test_get_gtsm_data(rio_region, tmp_path):
    start_time = datetime(2010, 1, 1)
    end_time = datetime(2010, 2, 1)

    params = {"start_time": start_time, "end_time": end_time}

    region = rio_region.as_posix()
    data_dir = Path(tmp_path, "gtsm_data")

    rule = GetGTSMData(region=region, data_root=data_dir, **params)

    rule.run_with_checks()


def test_create_tide_surge_timeseries(waterlevel_timeseries, tmp_path):
    data_dir = Path(tmp_path, "waterlevel")
    data_dir.mkdir()
    waterlevel_timeseries.to_netcdf(data_dir / "waterlevel_timeseries.nc")
    waterlevel_timeseries.close()

    rule = TideSurgeTimeseries(
        waterlevel_timeseries=data_dir / "waterlevel_timeseries.nc",
        data_root=data_dir,
    )

    rule.run_with_checks()


def test_get_coast_rp(rio_region, tmp_path):
    data_dir = Path(tmp_path, "coast_rp")
    # TODO: Fix hard coded path, include coast-rp in test data?
    coast_rp_fn = Path(r"p:\11209169-003-up2030\data\WATER_LEVEL\COAST-RP\COAST-RP.nc")

    rule = GetCoastRP(region=rio_region, data_root=data_dir, coastrp_fn=coast_rp_fn)

    rule.run_with_checks()


def test_get_waterlevel_rps(waterlevel_timeseries, tmp_path):
    data_dir = Path(tmp_path, "waterlevel")
    data_dir.mkdir()
    waterlevel_timeseries.to_netcdf(data_dir / "waterlevel_timeseries.nc")
    waterlevel_timeseries.close()

    rule = GetWaterlevelRPS(
        waterlevel_timeseries=data_dir / "waterlevel_timeseries.nc", data_root=data_dir
    )

    rule.run_with_checks()


def test_coastal_design_events(tide_surge_timeseries, rps_nc, tmp_path):
    data_dir = Path(tmp_path, "coastal_rps")
    data_dir.mkdir()
    t, s = tide_surge_timeseries
    t.to_netcdf(data_dir / "tide_timeseries.nc")
    s.to_netcdf(data_dir / "surge_timeseries.nc")

    rps_nc.to_netcdf(data_dir / "waterlevel_rps.nc")

    rule = CoastalDesignEvents(data_root=data_dir, event_folder=data_dir / "events")

    rule.run_with_checks()
