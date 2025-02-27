import platform
from pathlib import Path

import pytest
from hydromt_wflow import WflowModel

from hydroflows.methods.wflow import WflowBuild, WflowRun, WflowUpdateForcing


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
@pytest.mark.parametrize("copy_model", [True, False])
def test_wflow_update_forcing(
    wflow_tmp_model: Path, global_catalog: Path, copy_model: bool
):
    # required inputs
    wflow_toml = Path(wflow_tmp_model, "wflow_sbm.toml")
    start_time = "2020-02-01"
    end_time = "2020-02-10"
    # Check output dir if subdir of wflow dir
    output_dir1 = wflow_tmp_model / "sim"
    # Check output dir if not subdir of wflow dir
    output_dir2 = wflow_tmp_model.parent / "sim"
    # additional param
    catalog_path = global_catalog.as_posix()

    rule = WflowUpdateForcing(
        wflow_toml=wflow_toml,
        start_time=start_time,
        end_time=end_time,
        catalog_path=catalog_path,
        output_dir=output_dir1,
        copy_model=copy_model,
    )

    assert rule.output.wflow_out_toml == rule.params.output_dir / "wflow_sbm.toml"

    rule.run_with_checks()

    # This should fail when copy model == False
    if not copy_model:
        with pytest.raises(
            ValueError,
            match="Output directory must be relative to input directory when not copying model.",
        ):
            rule = WflowUpdateForcing(
                wflow_toml=wflow_toml,
                start_time=start_time,
                end_time=end_time,
                catalog_path=catalog_path,
                output_dir=output_dir2,
                copy_model=copy_model,
            )
    else:
        rule = WflowUpdateForcing(
            wflow_toml=wflow_toml,
            start_time=start_time,
            end_time=end_time,
            catalog_path=catalog_path,
            output_dir=output_dir1,
            copy_model=copy_model,
        )
        assert rule.output.wflow_out_toml == rule.params.output_dir / "wflow_sbm.toml"
        rule.run_with_checks()


@pytest.mark.slow()
@pytest.mark.requires_test_data()
@pytest.mark.parametrize("method", ["docker", "exe", "julia", "apptainer"])
def test_wflow_run(
    wflow_sim_model: Path,
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
    )
    assert wf_run.output.wflow_output_timeseries == wflow_scalar
    wf_run.run_with_checks()
