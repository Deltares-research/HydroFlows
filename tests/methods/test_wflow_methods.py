import shutil
from pathlib import Path

import pytest

from hydroflows.methods.wflow import WflowBuild, WflowDesignHydro, WflowUpdateForcing


@pytest.mark.requires_data()
def test_wflow_build(rio_region: Path, rio_test_data: Path, tmp_path: Path):
    # required inputs
    region = rio_region.as_posix()
    wflow_root = Path(tmp_path, "wflow_model")

    # some additional params
    data_libs = rio_test_data.as_posix()
    gauges = None
    upstream_area = 10
    plot_fig = False

    rule = WflowBuild(
        region=region,
        wflow_root=wflow_root,
        data_libs=data_libs,
        gauges=gauges,
        upstream_area=upstream_area,
        plot_fig=plot_fig,
    )

    rule.run_with_checks()

    # FIXME: add params gauges, then uncomment this
    # fn_geoms = Path(fn_wflow_toml.parent, "staticgeoms", "gauges_locs.geojson")
    # assert fn_geoms.exists()


@pytest.mark.requires_data()
def test_wflow_update_forcing(
    rio_wflow_model: Path, rio_test_data: Path, tmp_path: Path
):
    # copy the wflow model to the tmp_path
    root = tmp_path / "model"
    shutil.copytree(rio_wflow_model.parent, root)
    # required inputs
    wflow_toml = Path(root, rio_wflow_model.name)
    start_time = "2020-02-01"
    end_time = "2020-02-10"

    # additional param
    data_libs = rio_test_data.as_posix()

    rule = WflowUpdateForcing(
        wflow_toml=wflow_toml,
        start_time=start_time,
        end_time=end_time,
        data_libs=data_libs,
    )

    rule.run_with_checks()


def test_wflow_design_hydro(tmp_disch_time_series_nc: Path, tmp_path: Path):
    # required inputs
    discharge_nc = tmp_disch_time_series_nc
    event_root = Path(tmp_path, "events")

    m = WflowDesignHydro(
        discharge_nc=discharge_nc,
        event_root=event_root,
        wildcard="q_event",
    )
    assert "{q_event}" in str(m.output.event_csv)
    m.run_with_checks()
