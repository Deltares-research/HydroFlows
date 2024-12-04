import shutil
from pathlib import Path

import pytest

from hydroflows.methods.wflow import WflowBuild, WflowUpdateForcing


@pytest.mark.requires_data()
def test_wflow_build(
    region: Path, build_cfgs: dict, global_catalog: Path, tmp_path: Path
):
    # required inputs
    region = region.as_posix()
    wflow_root = Path(tmp_path, "wflow_model")

    # some additional params
    data_libs = global_catalog.as_posix()
    gauges = None
    plot_fig = False

    rule = WflowBuild(
        region=region,
        config=build_cfgs["wflow_build"],
        gauges=gauges,
        wflow_root=wflow_root,
        data_libs=data_libs,
        plot_fig=plot_fig,
    )

    rule.run_with_checks()

    # FIXME: add params gauges, then uncomment this
    # fn_geoms = Path(fn_wflow_toml.parent, "staticgeoms", "gauges_locs.geojson")
    # assert fn_geoms.exists()


@pytest.mark.requires_data()
def test_wflow_update_forcing(
    wflow_test_model: Path, global_catalog: Path, tmp_path: Path
):
    # copy the wflow model to the tmp_path
    root = tmp_path / "model"
    shutil.copytree(wflow_test_model, root)
    # required inputs
    wflow_toml = Path(root, "wflow_sbm.toml")
    start_time = "2020-02-01"
    end_time = "2020-02-10"

    # additional param
    data_libs = global_catalog.as_posix()

    rule = WflowUpdateForcing(
        wflow_toml=wflow_toml,
        start_time=start_time,
        end_time=end_time,
        data_libs=data_libs,
    )

    rule.run_with_checks()
