from pathlib import Path

from hydroflows.methods.discharge import FluvialDesignEvents


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
