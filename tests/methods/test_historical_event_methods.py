import logging
from pathlib import Path

import pytest

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

    # Testing multiple forcings
    hist_events_multiple = HistoricalEvents(
        discharge_nc=tmp_disch_time_series_nc,
        precip_nc=tmp_precip_time_series_nc,  # Note: outside of the event period
        water_level_nc=temp_waterlevel_timeseries_nc,
        events_dates=events_dates,
        water_level_index_dim="stations",
        output_dir=Path(tmp_path, "multiple_forcings"),
    )

    hist_events_multiple.run()

    assert (
        "Time slice for event 'historical_event01' (for driver rainfall from 2000-01-02 00:00:00 to 2000-01-04 02:00:00) returns no data."
        in caplog.text
    )

    # Testing one forcing
    hist_events_single = HistoricalEvents(
        discharge_nc=tmp_disch_time_series_nc,
        events_dates=events_dates,
        output_dir=Path(tmp_path, "single_forcing"),
    )

    hist_events_single.run()

    # Testing pydantic validation error for no input timeseries
    with pytest.raises(ValueError, match="At least one of the input files"):
        HistoricalEvents(events_dates=events_dates).run()
