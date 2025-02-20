import platform
from pathlib import Path

import pytest
import xarray as xr
from hydromt_wflow import WflowModel

from hydroflows.methods.wflow import (
    WflowBuild,
    WflowRun,
    WflowUpdateChangeFactors,
    WflowUpdateForcing,
)


@pytest.mark.requires_test_data()
@pytest.mark.slow()
def test_wflow_build(
    region: Path, build_cfgs: dict, global_catalog: Path, tmp_path: Path
):
    # required inputs
    region = region.as_posix()
    wflow_root = Path(tmp_path, "wflow_model")

    # some additional params
    catalog_path = global_catalog.as_posix()
    gauges = None
    plot_fig = False

    rule = WflowBuild(
        region=region,
        config=build_cfgs["wflow_build"],
        gauges=gauges,
        wflow_root=wflow_root,
        catalog_path=catalog_path,
        plot_fig=plot_fig,
    )

    rule.run_with_checks()

    # FIXME: add params gauges, then uncomment this
    # fn_geoms = Path(fn_wflow_toml.parent, "staticgeoms", "gauges_locs.geojson")
    # assert fn_geoms.exists()


@pytest.mark.requires_test_data()
def test_wflow_update_factors(
    tmp_path: Path,
    cmip6_stats: list,
    wflow_cached_model: Path,
):
    rule = WflowUpdateChangeFactors(
        dataset=Path(
            cmip6_stats,
            "change_factor",
            "change_NOAA-GFDL_GFDL-ESM4_ssp585_2090-2100.nc",
        ),
        wflow_toml=Path(wflow_cached_model, "wflow_sbm.toml"),
        output_dir=tmp_path,
    )
    rule.run_with_checks()

    assert rule.output.downscaled.is_file()
    ds = xr.open_dataset(rule.output.downscaled)
    assert int(ds["precip"].values.mean() * 100) == 102
    assert ds["latitude"].size == 200
    ds = None


@pytest.mark.requires_test_data()
def test_wflow_update_forcing(wflow_tmp_model: Path, global_catalog: Path):
    # required inputs
    wflow_toml = Path(wflow_tmp_model, "wflow_sbm.toml")
    start_time = "2020-02-01"
    end_time = "2020-02-10"

    # additional param
    catalog_path = global_catalog.as_posix()

    rule = WflowUpdateForcing(
        wflow_toml=wflow_toml,
        start_time=start_time,
        end_time=end_time,
        catalog_path=catalog_path,
    )

    rule.run_with_checks()


@pytest.mark.slow()
@pytest.mark.requires_test_data()
@pytest.mark.parametrize("method", ["docker", "exe", "julia", "script", "apptainer"])
def test_wflow_run(
    wflow_sim_model: Path,
    method: str,
    has_wflow_julia: bool,
    wflow_exe: Path,
    wflow_run_script: Path,
    has_docker: bool,
    has_apptainer: bool,
):
    # check if wflow julia is installed
    if (method == "julia" or method == "script") and not has_wflow_julia:
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
    wflow_toml = Path(wflow_sim_model, "wflow_sbm.toml")
    wflow_scalar = Path(wflow_toml.parent, "run_default", "output_scalar.nc")
    if wflow_scalar.is_file():
        wflow_scalar.unlink()

    wf = WflowModel(root=wflow_sim_model, mode="r+")
    wf.setup_config(
        **{"starttime": "2014-01-01T00:00:00", "endtime": "2014-01-02T00:00:00"}
    )
    wf.write_config()
    assert wflow_toml.is_file()

    wf_run = WflowRun(
        wflow_toml=wflow_toml,
        julia_num_threads=2,
        run_method=method,
        wflow_bin=wflow_exe,
        wflow_run_script=wflow_run_script,
    )
    assert wf_run.output.wflow_output_timeseries == wflow_scalar
    wf_run.run_with_checks()
