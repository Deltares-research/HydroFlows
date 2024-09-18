from pathlib import Path

from hydroflows.methods.discharge import FluvialHistoricalEvents


def test_fluvial_historical_events(tmp_disch_time_series_nc: Path, tmp_path: Path):
    events_dates = {
        "q_event01": {"startdate": "1995-03-04", "enddate": "1995-03-05 14:00"},
        "q_event02": {"startdate": "2025-03-04", "enddate": "2025-03-07 17:00"},
    }

    q_events = FluvialHistoricalEvents(
        discharge_nc=tmp_disch_time_series_nc,
        events_dates=events_dates,
        event_root=Path(tmp_path, "data"),
    )

    q_events.run_with_checks()
