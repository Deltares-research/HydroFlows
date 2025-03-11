"""Testing for FIAT rules."""

import os
import platform
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
    rule.run()


@pytest.mark.requires_test_data()
@pytest.mark.parametrize("copy_model", [True, False])
def test_fiat_update_hazard(
    fiat_tmp_model: Path,
    hazard_map_data: xr.DataArray,
    event_set_file_pluvial: Path,
    tmp_path: Path,
    copy_model: bool,
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

    # Check output dir if subdir of fiat dir
    output_dir1 = fiat_tmp_model / "sim"
    # Check output dir if not subdir of fiat dir
    output_dir2 = fiat_tmp_model.parent / "sim"
    # Setup the method.
    rule = FIATUpdateHazard(
        fiat_cfg=fiat_cfg,
        event_set_yaml=event_set_file_pluvial,
        hazard_maps=hazard_maps,
        output_dir=output_dir1,
        copy_model=copy_model,
    )

    assert (
        rule.output.fiat_out_cfg
        == rule.params.output_dir / rule.params.sim_name / "settings.toml"
    )

    rule.run()

    # This should fail when copy model == False
    if not copy_model:
        with pytest.raises(
            ValueError,
            match="Output directory must be relative to input directory when not copying model.",
        ):
            rule = FIATUpdateHazard(
                fiat_cfg=fiat_cfg,
                event_set_yaml=event_set_file_pluvial,
                hazard_maps=hazard_maps,
                output_dir=output_dir2,
                copy_model=copy_model,
            )
    else:
        rule = FIATUpdateHazard(
            fiat_cfg=fiat_cfg,
            event_set_yaml=event_set_file_pluvial,
            hazard_maps=hazard_maps,
            output_dir=output_dir2,
            copy_model=copy_model,
        )
        assert (
            rule.output.fiat_out_cfg
            == rule.params.output_dir / rule.params.sim_name / "settings.toml"
        )

    rule.run()


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
    rule.run()

    assert fiat_cfg.exists()


@pytest.mark.requires_test_data()
def test_fiat_visualize_risk_event(fiat_tmp_model_all: Path, tmp_path: Path):
    fiat_output = Path(
        fiat_tmp_model_all / "simulations" / "pluvial_events" / "output" / "output.csv"
    )
    base_fiat_model = fiat_output.parent.parent.parent.parent
    fiat_cfg = Path(fiat_output.parent.parent / "settings.toml")
    fiat_spatial_joins = Path(
        fiat_output.parent.parent.parent.parent / "spatial_joins.toml"
    )

    # Visualize output
    output_dir = tmp_path / "fiat_visualize"
    rule = FIATVisualize(
        fiat_output_csv=fiat_output,
        fiat_cfg=fiat_cfg,
        spatial_joins_cfg=fiat_spatial_joins,
        output_dir=output_dir,
    )
    rule.run()

    # check if non-listed aggregation files are in output folder
    # (total metrics are already checked as these are listed in FiatVisualize.output)
    output_files = [Path(filename).name for filename in os.listdir(output_dir)]
    assert "Infometrics_pluvial_events_default_aggregation.csv" in output_files
    assert "default_aggregation_total_damages_pluvial_events.geojson" in output_files
    assert (
        "default_aggregation_total_damages_pluvial_events_ExpectedAnnualDamages.png"
        in output_files
    )

    # Assert expected output metrics are in csv infometrics
    with open((base_fiat_model / "spatial_joins.toml"), "r") as f:
        spatial_joins = toml.load(f)
    aggregation = spatial_joins["aggregation_areas"][0]["name"]
    infometric_files = [fn for fn in os.listdir(output_dir) if fn.endswith(".csv")]
    for file in infometric_files:
        infometric_file = pd.read_csv(Path(output_dir / file))
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
