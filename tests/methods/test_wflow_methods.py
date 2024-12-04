import platform
import shutil
import subprocess
from pathlib import Path

import pytest
from hydromt_wflow import WflowModel

from hydroflows.methods.wflow import WflowBuild, WflowRun, WflowUpdateForcing


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


@pytest.mark.requires_data()
@pytest.mark.skipif(True, reason="requires complete wflow model instance")
def test_wflow_run_julia(rio_wflow_model: Path, tmp_path: Path):
    # check if wflow julia is installed
    s = subprocess.run(["julia", "-e", "using Wflow"])
    if s.returncode != 0:
        pytest.skip("Wflow Julia is not installed.")
    # copy the wflow model to the tmp_path
    root = tmp_path / "model"
    shutil.copytree(rio_wflow_model.parent, root)
    wflow_toml = Path(root, rio_wflow_model.name)

    # run the model
    rule = WflowRun(wflow_toml=wflow_toml, wflow_julia=True)
    rule.run_with_checks()


@pytest.mark.requires_data()
@pytest.mark.skipif(
    platform.system() != "Linux", reason="Docker running only supported on Linux"
)
def test_wflow_run_linux(wflow_tmp_root: Path):
    wflow_toml = Path(wflow_tmp_root, "simulations", "default", "wflow_sbm.toml")
    wflow_scalar = Path(wflow_toml.parent, "run_default", "output_scalar.nc")

    wf = WflowModel(root=wflow_toml.parent, mode="r+")
    wf.setup_config(
        **{"starttime": "2014-01-01T00:00:00", "endtime": "2014-01-01T00:00:00"}
    )
    wf.write_config()

    assert wflow_toml.is_file()
    wf_run = WflowRun(wflow_toml=wflow_toml, vm="docker", docker_tag="v0.8.1")
    assert wf_run.output.wflow_output_timeseries == wflow_scalar
    wf_run.run_with_checks()
