from pathlib import Path

import pandas as pd
import xarray as xr

from hydroflows.events import EventSet
from hydroflows.methods.rainfall import (
    FutureClimateRainfall,
    GetERA5Rainfall,
    PluvialDesignEvents,
    PluvialDesignEventsGPEX,
    PluvialHistoricalEvents,
)


def test_pluvial_design_hyeto(tmp_precip_time_series_nc: Path, tmp_path: Path):
    rps = [1, 10, 100]
    p_events = PluvialDesignEvents(
        precip_nc=tmp_precip_time_series_nc,
        event_root=Path(tmp_path, "data"),
        rps=rps,
        ev_type="BM",
        distribution="gev",
        duration=24,
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
    fn_csv = tmp_precip_time_series_nc.parent / filename
    df = pd.read_csv(fn_csv, parse_dates=True, index_col=0)
    assert df.max().max() == 1.0


def test_pluvial_design_hyeto_gpex(region: Path, gpex_data: Path, tmp_path: Path):
    rps = [20, 39, 100]
    p_events = PluvialDesignEventsGPEX(
        gpex_nc=str(gpex_data),
        region=str(region),
        event_root=Path(tmp_path, "events"),
        rps=rps,
        duration=120,
    )

    assert len(p_events.params.event_names) == len(rps)

    p_events.run_with_checks()


def test_get_ERA5_rainfall(region: Path, tmp_path: Path):
    get_era5 = GetERA5Rainfall(
        region=str(region),
        data_root=str(tmp_path / "data"),
        filename="era5.nc",
        start_date="2023-11-01",
        end_date="2023-12-31",
    )
    assert get_era5.output.precip_nc == tmp_path / "data" / "era5.nc"
    get_era5.run_with_checks()

    da = xr.open_dataarray(get_era5.output.precip_nc)
    assert da["time"].min() == pd.Timestamp("2023-11-01")


def test_pluvial_historical_events(tmp_precip_time_series_nc: Path, tmp_path: Path):
    events_dates = {
        # The first event is outside the available time series to test warning coverage.
        "p_event01": {"startdate": "1995-03-04 12:00", "enddate": "1995-03-05 14:00"},
        "p_event02": {"startdate": "2005-03-04 09:00", "enddate": "2005-03-07 17:00"},
        # The last event is partially overlapping the available time series to test warning coverage.
        "p_event03": {"startdate": "1999-12-20 09:00", "enddate": "2001-01-07 17:00"},
    }

    p_events = PluvialHistoricalEvents(
        precip_nc=tmp_precip_time_series_nc,
        events_dates=events_dates,
        event_root=Path(tmp_path, "data"),
    )

    p_events.run_with_checks()


def test_future_climate_rainfall(
    test_data_dir: Path,
    tmp_path: Path,
):
    event_set_yaml = test_data_dir / "events.yml"

    out_root = Path(tmp_path / "CC_scaling")

    rule = FutureClimateRainfall(
        event_set_yaml=event_set_yaml,
        scenario_name="RCP85",
        dT=2.5,
        event_root=out_root,
        time_col="date",
    )

    rule.run_with_checks()

    fn_scaled_event_set = rule.output.future_event_set_yaml
    scaled_event_set = EventSet.from_yaml(fn_scaled_event_set)
    assert isinstance(scaled_event_set.events, list)

    # are all paths absolute
    assert all([Path(event["path"]).is_absolute() for event in scaled_event_set.events])
    assert all([Path(event["path"]).exists() for event in scaled_event_set.events])
