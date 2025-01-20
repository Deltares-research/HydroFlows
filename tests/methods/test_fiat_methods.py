"""Testing for FIAT rules."""

import platform
from os import walk
from pathlib import Path

import pandas as pd
import pytest
import toml
import xarray as xr

from hydroflows.methods.fiat import FIATBuild, FIATRun, FIATUpdateHazard, FIATVisualize


@pytest.mark.requires_test_data()
def test_fiat_build(tmp_path: Path, sfincs_test_region: Path, build_cfgs: dict):
    # Setting input data
    region = sfincs_test_region.as_posix()
    fiat_root = Path(tmp_path, "fiat_model")

    # Setup the rule
    rule = FIATBuild(
        region=region, config=build_cfgs["fiat_build"], fiat_root=fiat_root
    )
    rule.run_with_checks()


@pytest.mark.requires_test_data()
def test_fiat_update_hazard(
    fiat_tmp_model: Path,
    hazard_map_data: xr.DataArray,
    event_set_file: Path,
    tmp_path: Path,
):
    # Specify in- and output
    fiat_cfg = Path(fiat_tmp_model) / "settings.toml"

    # create hazard maps
    # NOTE file names should match the event names in the event set
    hazard_maps = []
    for i in range(3):
        nc_file = tmp_path / f"flood_map_p_event{i+1:02d}.nc"
        hazard_map_data.to_netcdf(nc_file)
        hazard_maps.append(nc_file)

    # Setup the method.
    rule = FIATUpdateHazard(
        fiat_cfg=fiat_cfg,
        event_set_yaml=event_set_file,
        hazard_maps=hazard_maps,
    )
    rule.run_with_checks()


@pytest.mark.requires_test_data()
@pytest.mark.parametrize("method", ["python", "exe"])
def test_fiat_run(
    fiat_sim_model: Path, method: str, fiat_exe: Path, has_fiat_python: bool
):
    if method == "exe" and not fiat_exe.is_file():
        pytest.skip(f"FIAT executable not found at {fiat_exe}")
    elif method == "exe" and platform.system() != "Windows":
        pytest.skip("FIAT exe only supported on Windows")
    # elif method == "python" and not has_fiat_python:
    #    pytest.skip("FIAT python package not found")
    elif method == "python" and platform.system() != "Windows":
        # FIXME: FIAT python does currently not work on Linux
        # when reading the vulnerability curves
        # ERROR: Cannot cast array data from dtype("<U32") to dtype("float64") according to the rule "safe"
        pytest.skip("FIAT python does currently not work on Linux..")

    # specify in- and output
    fiat_cfg = Path(
        fiat_sim_model,
        "settings.toml",
    )
    # Setup the method
    rule = FIATRun(fiat_cfg=fiat_cfg, fiat_exe=fiat_exe, run_method=method)
    rule.run_with_checks()

    assert fiat_cfg.exists()


@pytest.mark.requires_test_data()
@pytest.mark.parametrize("method", ["python", "exe"])
def test_fiat_visualize_single_event(
    fiat_sim_model: Path,
    sfincs_sim_model: Path,
    event_set_file: Path,
    fiat_exe: Path,
    method: str,
):
    fiat_cfg = Path(fiat_sim_model) / "settings.toml"

    # Visualize output
    rule = FIATVisualize(fiat_cfg=fiat_cfg, event_set_file=event_set_file)
    rule.run_with_checks()
    visual_output_fn = next(walk(Path(fiat_tmp_model) / "fiat_metrics"))[-1]

    # Assert all infometrics and infographic files are in output folder
    assert "geojson" in visual_output_fn
    assert "html" in visual_output_fn
    assert "csv" in visual_output_fn

    # Assert total and aggregated metrics output exists
    infometrics = [i for i in visual_output_fn if i.endswith(".csv")]
    assert len(infometrics) == 2

    # Assert expected output metrics are in csv infometrics
    with open((fiat_cfg.parent / "spatial_joins.toml"), "r") as f:
        spatial_joins = toml.load(f)
    aggregation = spatial_joins["aggregation_areas"][0]["name"]

    for file in infometrics:
        infometric_file = pd.read_csv(file)
        if aggregation in file:
            assert "TotalDamage" in infometric_file.columns
            assert "ExpectedAnnualDamages" in infometric_file.columns
            assert "FloodedHomes" in infometric_file.columns
        else:
            assert "TotalDamage" in infometric_file.iloc[:, 0]
            assert "ExpectedAnnualDamage" in infometric_file.iloc[:, 0]
