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
@pytest.mark.parametrize("method", ["docker", "exe", "julia", "apptainer"])
def test_wflow_run(
    wflow_sim_tmp_root: Path,
    method: str,
    has_wflow_julia: bool,
    wflow_exe: Path,
    has_docker: bool,
    has_apptainer: bool,
):
    # check if wflow julia is installed
    if method == "julia" and not has_wflow_julia:
        pytest.skip("Wflow Julia is not installed.")
    elif method == "exe" and wflow_exe.is_file() is False:
        pytest.skip(f"Wflow executable is not available {wflow_exe}")
    elif method == "exe" and platform.system() != "Windows":
        pytest.skip("Wflow exe only supported on Windows")
    elif method == "docker" and has_docker is False:
        pytest.skip("Docker is not available.")
    elif method == "apptainer" and has_apptainer is False:
        pytest.skip("Apptainer is not available.")

    # run the model
    wflow_toml = Path(wflow_sim_tmp_root, "wflow_sbm.toml")
    wflow_scalar = Path(wflow_toml.parent, "run_default", "output_scalar.nc")
    if wflow_scalar.is_file():
        wflow_scalar.unlink()

    wf = WflowModel(root=wflow_sim_tmp_root, mode="r+")
    wf.setup_config(
        **{"starttime": "2014-01-01T00:00:00", "endtime": "2014-01-02T00:00:00"}
    )
    wf.write_config()
    assert wflow_toml.is_file()

    wf_run = WflowRun(wflow_toml=wflow_toml, julia_num_threads=2, run_method=method)
    assert wf_run.output.wflow_output_timeseries == wflow_scalar
    wf_run.run_with_checks()
