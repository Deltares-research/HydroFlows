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

    events_dates = {
        "historical_event01": {
            "startdate": "2000-01-02 00:00",
            "enddate": "2000-01-04 02:00",
        },
    }

    hist_events = HistoricalEvents(
        discharge_nc=tmp_disch_time_series_nc,
        precip_nc=tmp_precip_time_series_nc,
        water_level_nc=temp_waterlevel_timeseries_nc,
        events_dates=events_dates,
        water_level_index_dim="stations",
        event_root=Path(tmp_path, "data"),
    )

    hist_events.run_with_checks()

    assert (
        "Time slice for event 'historical_event01' (for driver rainfall from 2000-01-02 00:00:00 to 2000-01-04 02:00:00) returns no data."
        in caplog.text
    )
