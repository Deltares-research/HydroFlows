from pathlib import Path

from hydroflows.methods.discharge import FluvialDesignEvents, FluvialHistoricalEvents


def test_fluvial_design_hydro(tmp_disch_time_series_nc: Path, tmp_path: Path):
    # required inputs
    discharge_nc = tmp_disch_time_series_nc
    event_root = Path(tmp_path, "events")

    m = FluvialDesignEvents(
        discharge_nc=discharge_nc,
        event_root=event_root,
        wildcard="q_event",
        var_name="Q",
    )
    assert "{q_event}" in str(m.output.event_csv)
    m.run_with_checks()


def test_fluvial_historical_events(tmp_disch_time_series_nc: Path, tmp_path: Path):
    events_dates = {
        # The first event is outside the available time series to test warning coverage.
        "q_event01": {"startdate": "1995-03-04", "enddate": "1995-03-05 14:00"},
        "q_event02": {"startdate": "2025-03-04", "enddate": "2025-03-07 17:00"},
    }

    q_events = FluvialHistoricalEvents(
        discharge_nc=tmp_disch_time_series_nc,
        events_dates=events_dates,
        event_root=Path(tmp_path, "data"),
    )

    q_events.run_with_checks()
