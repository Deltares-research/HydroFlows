from datetime import datetime
from pathlib import Path
from typing import Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import Point

from hydroflows.methods.coastal.coastal_design_events import CoastalDesignEvents
from hydroflows.methods.coastal.coastal_design_events_from_rp_data import (
    CoastalDesignEventFromRPData,
)
from hydroflows.methods.coastal.coastal_tidal_analysis import CoastalTidalAnalysis
from hydroflows.methods.coastal.get_coast_rp import GetCoastRP
from hydroflows.methods.coastal.get_gtsm_data import GetGTSMData

catalog_path = Path(r"p:\11209169-003-up2030\data\WATER_LEVEL\data_catalog.yml")


@pytest.fixture()
def waterlevel_timeseries() -> xr.DataArray:
    dates = pd.date_range(start="2000-01-01", end="2015-12-31", freq="10min")

    np.random.seed(1234)
    data = np.random.rand(len(dates))

    da = xr.DataArray(
        data=data,
        dims=("time"),
        coords={"time": dates},
        name="h",
    )
    da = da.expand_dims(dim={"stations": 1})
    return da


@pytest.fixture()
def tide_surge_timeseries() -> Tuple[xr.DataArray, xr.DataArray]:
    dates = pd.date_range(start="2000-01-01", end="2005-12-31", freq="10min")

    np.random.seed(1234)
    data1 = np.random.rand(len(dates))
    np.random.seed(5678)
    data2 = np.random.rand(len(dates))

    t = xr.DataArray(data=data1, dims=("time"), coords={"time": dates}, name="t")
    s = xr.DataArray(data=data2, dims=("time"), coords={"time": dates}, name="s")
    t = t.expand_dims(dim={"stations": 1})
    s = s.expand_dims(dim={"stations": 1})
    return t, s


@pytest.fixture()
def waterlevel_rps() -> xr.Dataset:
    rps = xr.Dataset(
        coords=dict(rps=("rps", [1, 10, 100])),
        data_vars=dict(return_values=(["rps"], np.array([0.5, 1, 1.5]))),
    )
    rps = rps.expand_dims(dim={"stations": 1})
    return rps


@pytest.fixture()
def bnd_locations() -> gpd.GeoDataFrame:
    bnds = gpd.GeoDataFrame(data={"stations": [1]}, geometry=[Point(1, 1)], crs=4326)
    return bnds


@pytest.mark.requires_data()
@pytest.mark.skipif(not catalog_path.exists(), reason="No access to Data Catalog")
def test_get_gtsm_data(region: Path, tmp_path: Path, catalog_path: Path = catalog_path):
    start_time = datetime(2010, 1, 1)
    end_time = datetime(2010, 2, 1)

    params = {"start_time": start_time, "end_time": end_time}

    region = region.as_posix()
    data_dir = Path(tmp_path, "gtsm_data")

    rule = GetGTSMData(
        region=region, gtsm_catalog=catalog_path, data_root=data_dir, **params
    )

    rule.run_with_checks()


@pytest.mark.slow()
def test_create_tide_surge_timeseries(
    waterlevel_timeseries: xr.DataArray, tmp_path: Path
):
    data_dir = Path(tmp_path, "waterlevel")
    data_dir.mkdir()
    waterlevel_timeseries.to_netcdf(data_dir / "waterlevel_timeseries.nc")
    waterlevel_timeseries.close()

    rule = CoastalTidalAnalysis(
        waterlevel_timeseries=data_dir / "waterlevel_timeseries.nc",
        data_root=data_dir,
    )

    rule.run_with_checks()


@pytest.mark.requires_data()
@pytest.mark.skipif(not catalog_path.exists(), reason="No access to Data Catalog")
def test_get_coast_rp(region: Path, tmp_path: Path, catalog_path: Path = catalog_path):
    data_dir = Path(tmp_path, "coast_rp")

    rule = GetCoastRP(region=region, coastrp_catalog=catalog_path, data_root=data_dir)

    rule.run_with_checks()


def test_coastal_design_events(
    tide_surge_timeseries: Tuple[xr.DataArray, xr.DataArray],
    bnd_locations: gpd.GeoDataFrame,
    tmp_path: Path,
):
    data_dir = Path(tmp_path, "coastal_rps")
    data_dir.mkdir()
    t, s = tide_surge_timeseries
    t.to_netcdf(data_dir / "tide_timeseries.nc")
    s.to_netcdf(data_dir / "surge_timeseries.nc")
    bnds = bnd_locations
    bnds.to_file(data_dir / "bnd_locations.gpkg", driver="GPKG")

    rule = CoastalDesignEvents(
        surge_timeseries=data_dir / "surge_timeseries.nc",
        tide_timeseries=data_dir / "tide_timeseries.nc",
        bnd_locations=data_dir / "bnd_locations.gpkg",
        event_root=str(data_dir),
    )

    rule.run_with_checks()


def test_coastal_event_from_rp_data(
    tide_surge_timeseries: Tuple[xr.DataArray, xr.DataArray],
    bnd_locations: gpd.GeoDataFrame,
    waterlevel_rps: xr.Dataset,
    tmp_path: Path,
):
    data_dir = Path(tmp_path, "coastal_events")
    data_dir.mkdir()
    t, s = tide_surge_timeseries
    t.to_netcdf(data_dir / "tide_timeseries.nc")
    s.to_netcdf(data_dir / "surge_timeseries.nc")

    bnds = bnd_locations
    bnds.to_file(data_dir / "bnd_locations.gpkg", driver="GPKG")

    rps = waterlevel_rps
    rps.to_netcdf(data_dir / "waterlevel_rps.nc")

    rule = CoastalDesignEventFromRPData(
        surge_timeseries=data_dir / "surge_timeseries.nc",
        tide_timeseries=data_dir / "tide_timeseries.nc",
        bnd_locations=data_dir / "bnd_locations.gpkg",
        rp_dataset=data_dir / "waterlevel_rps.nc",
        event_root=str(data_dir),
    )

    rule.run_with_checks()
