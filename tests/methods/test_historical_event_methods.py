import logging
from pathlib import Path

from hydroflows.methods.historical_events import HistoricalEvents


def test_historical_events(
    tmp_precip_time_series_nc: Path,
    tmp_disch_time_series_nc: Path,
    temp_waterlevel_timeseries_nc: Path,
    tmp_path: Path,
    caplog,
):
    caplog.set_level(logging.WARNING)
    events_info = {
        "q_event01": {
            "startdate": "2021-05-01 12:00",
            "enddate": "2021-05-24 12:00",
            "type": "discharge",
        },
        # This event is outside the available time series to test warning coverage
        "p_event01": {
            "startdate": "1995-03-04 12:00",
            "enddate": "1995-03-05 14:00",
            "type": "rainfall",
        },
        # This event is partially overlapping the available time series to test warning coverage.
        "p_event02": {
            "startdate": "1999-12-20 09:00",
            "enddate": "2001-01-07 17:00",
            "type": "rainfall",
        },
        "wl_event01": {
            "startdate": "2011-11-11 12:00",
            "enddate": "2011-11-12 12:00",
            "type": "water_level",
        },
    }

    hist_events = HistoricalEvents(
        discharge_nc=tmp_disch_time_series_nc,
        precip_nc=tmp_precip_time_series_nc,
        water_level_nc=temp_waterlevel_timeseries_nc,
        events_info=events_info,
        water_level_index_dim="stations",
        event_root=Path(tmp_path, "data"),
    )

    hist_events.run_with_checks()

    assert (
        "Time slice for event 'p_event01' (from 1995-03-04 12:00:00 to 1995-03-05 14:00:00) returns no data."
        in caplog.text
    )
    assert (
        "The selected series for the event 'p_event02' is shorter than anticipated"
        in caplog.text
    )
