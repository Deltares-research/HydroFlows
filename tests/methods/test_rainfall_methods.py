from pathlib import Path

import pandas as pd
import pytest
import xarray as xr

from hydroflows.methods.events import EventSet
from hydroflows.methods.rainfall import (
    FutureClimateRainfall,
    GetERA5Rainfall,
    PluvialDesignEvents,
    PluvialDesignEventsGPEX,
)
from hydroflows.workflow.wildcards import resolve_wildcards


def test_pluvial_design_events(tmp_precip_time_series_nc: Path, tmp_path: Path):
    rps = [2, 10, 100]
    p_events = PluvialDesignEvents(
        precip_nc=tmp_precip_time_series_nc,
        event_root=Path(tmp_path, "data"),
        rps=rps,
        ev_type="BM",
        distribution="gev",
        duration=24,
    )

    assert len(p_events.params.event_names) == len(rps)

    p_events.run()

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
    event = event_set.get_event("p_event_rp002")
    filename = event.forcings[0].path
    fn_csv = tmp_precip_time_series_nc.parent / filename
    df = pd.read_csv(fn_csv, parse_dates=True, index_col=0)
    assert df.max().max() == 1.0


@pytest.mark.requires_test_data()
def test_pluvial_design_events_gpex(region: Path, gpex_data: Path, tmp_path: Path):
    rps = [20, 39, 100]
    p_events = PluvialDesignEventsGPEX(
        gpex_nc=str(gpex_data),
        region=str(region),
        event_root=Path(tmp_path, "events"),
        rps=rps,
        duration=120,
    )

    assert len(p_events.params.event_names) == len(rps)

    p_events.run()


def test_get_ERA5_rainfall(region: Path, tmp_path: Path):
    get_era5 = GetERA5Rainfall(
        region=str(region),
        output_dir=str(tmp_path / "data"),
        filename="era5.nc",
        start_date="2023-11-01",
        end_date="2023-12-31",
    )
    assert get_era5.output.precip_nc == tmp_path / "data" / "era5.nc"
    get_era5.run()

    da = xr.open_dataarray(get_era5.output.precip_nc)
    assert da["time"].min() == pd.Timestamp("2023-11-01")


def test_future_climate_rainfall(
    tmp_path: Path,
    event_set_file: Path,
):
    out_root = Path(tmp_path / "CC_scaling")

    fut_clim_rain = FutureClimateRainfall(
        event_set_yaml=event_set_file,
        scenarios={"RCP4.5": 1.0, "RCP8.5": 1.5},
        event_root=out_root,
    )

    fut_clim_rain.run()

    fn_scaled_event_set = resolve_wildcards(
        fut_clim_rain.output.future_event_set_yaml, {"scenario": "RCP4.5"}
    )
    scaled_event_set = EventSet.from_yaml(fn_scaled_event_set)
    assert isinstance(scaled_event_set.events, list)

    # are all paths absolute
    assert all([Path(event["path"]).is_absolute() for event in scaled_event_set.events])
    assert all([Path(event["path"]).exists() for event in scaled_event_set.events])
