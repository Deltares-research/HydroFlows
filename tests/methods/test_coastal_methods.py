from datetime import datetime
from pathlib import Path
from typing import Tuple

import geopandas as gpd
import pytest
import xarray as xr

from hydroflows.events import EventSet
from hydroflows.methods.coastal.coastal_design_events import CoastalDesignEvents
from hydroflows.methods.coastal.coastal_design_events_from_rp_data import (
    CoastalDesignEventFromRPData,
)
from hydroflows.methods.coastal.coastal_tidal_analysis import CoastalTidalAnalysis
from hydroflows.methods.coastal.future_slr import FutureSLR
from hydroflows.methods.coastal.get_coast_rp import GetCoastRP
from hydroflows.methods.coastal.get_gtsm_data import GetGTSMData


@pytest.mark.requires_test_data()
def test_get_gtsm_data(region: Path, tmp_path: Path, global_catalog: Path):
    start_time = datetime(2010, 1, 1)
    end_time = datetime(2010, 2, 1)

    params = {"start_time": start_time, "end_time": end_time}

    region = region.as_posix()
    data_dir = Path(tmp_path, "gtsm_data")

    rule = GetGTSMData(
        region=region, gtsm_catalog=global_catalog, data_root=data_dir, **params
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


@pytest.mark.requires_test_data()
def test_get_coast_rp(region: Path, tmp_path: Path, global_catalog):
    data_dir = Path(tmp_path, "coast_rp")

    rule = GetCoastRP(region=region, coastrp_catalog=global_catalog, data_root=data_dir)

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
        rps=[1, 10, 50],
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


def test_future_climate_sea_level(
    test_data_dir: Path,
    tmp_path: Path,
):
    event_set_yaml = test_data_dir / "event-sets" / "coastal_events.yml"

    out_root = Path(tmp_path / "future_climate_sea_level")

    rule = FutureSLR(
        event_set_yaml=event_set_yaml,
        scenario_name="RCP85",
        slr_value=50,
        slr_unit="cm",
        event_root=out_root,
    )

    rule.run_with_checks()

    fn_scaled_event_set = rule.output.future_event_set_yaml
    scaled_event_set = EventSet.from_yaml(fn_scaled_event_set)
    assert isinstance(scaled_event_set.events, list)

    # are all paths absolute
    assert all([Path(event["path"]).is_absolute() for event in scaled_event_set.events])
    assert all([Path(event["path"]).exists() for event in scaled_event_set.events])
