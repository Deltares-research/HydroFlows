"""Testing for FIAT rules."""

import os
import platform
import shutil
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
    predefined_catalogs = ["artifact_data"]
    # Setup the rule
    rule = FIATBuild(
        region=region,
        config=build_cfgs["fiat_build"],
        fiat_root=fiat_root,
        predefined_catalogs=predefined_catalogs,
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
    elif method == "python" and not has_fiat_python:
        pytest.skip("FIAT python package not found")
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


def test_fiat_visualize_risk_event(
    fiat_cached_model: Path,
    event_set_file: Path,
):
    fiat_output = Path(
        fiat_cached_model / "simulations" / "pluvial_events" / "output" / "output.csv"
    )
    base_fiat_model = fiat_output.parent.parent.parent.parent

    # Remove output files if already exist
    mandatory_output_files = ["output.csv", "spatial.gpkg", "fiat.log"]
    output_files = os.listdir(fiat_output.parent)
    for file in output_files:
        file_name = Path(fiat_output.parent / file)
        if os.path.isdir(file_name):
            shutil.rmtree(file_name)
        else:
            if file not in mandatory_output_files:
                os.remove(file_name)

    # Visualize output
    rule = FIATVisualize(
        fiat_output=fiat_output,
        event_set_file=event_set_file,
        base_fiat_model=base_fiat_model,
    )
    rule.run_with_checks()
    output_files = os.listdir(fiat_output.parent)

    # Assert all infometrics and infographic files are in output folder
    file_extensions = []
    for file in output_files:
        file_extensions.append(os.path.splitext(file)[-1])

    assert ".geojson" in file_extensions
    assert ".html" in file_extensions
    assert ".csv" in file_extensions
    assert ".png" in file_extensions

    # Assert total and aggregated metrics output exists
    infometrics = [
        i for i in output_files if i.startswith("Infometrics") and i.endswith(".csv")
    ]
    assert len(infometrics) == 2

    # Assert expected output metrics are in csv infometrics
    with open((base_fiat_model / "spatial_joins.toml"), "r") as f:
        spatial_joins = toml.load(f)
    aggregation = spatial_joins["aggregation_areas"][0]["name"]

    for file in infometrics:
        infometric_file = pd.read_csv(Path(fiat_output.parent / file))
        if aggregation in file:
            assert infometric_file.columns.str.contains("TotalDamageRP").any()
            assert infometric_file.columns.str.contains("ExpectedAnnualDamages").any()
            assert infometric_file.columns.str.contains("FloodedHomes").any()
            assert infometric_file.columns.str.contains("FloodedBusinesses").any()
            assert infometric_file.columns.str.contains("FloodedIndustry").any()
        else:
            assert infometric_file.iloc[:, 0].str.contains("TotalDamageRP").any()
            assert infometric_file.iloc[:, 0].str.contains("ExpectedAnnualDamage").any()
            assert infometric_file.iloc[:, 0].str.contains("FloodedHomes").any()
            assert infometric_file.iloc[:, 0].str.contains("FloodedBusinesses").any()
            assert infometric_file.iloc[:, 0].str.contains("FloodedIndustry").any()
