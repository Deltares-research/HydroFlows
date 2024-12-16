"""Testing for FIAT rules."""

import platform
from pathlib import Path

import pytest

from hydroflows.methods.fiat import FIATBuild, FIATRun, FIATUpdateHazard


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
    first_hazard_map: Path,
    second_hazard_map: Path,
    event_set_file: Path,
):
    # Specify in- and output
    fiat_cfg = Path(fiat_tmp_model) / "settings.toml"
    # Setup the method.
    rule = FIATUpdateHazard(
        fiat_cfg=fiat_cfg,
        event_set_yaml=event_set_file,
        hazard_maps=[first_hazard_map, second_hazard_map],
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
        # ERROR: Cannot cast array data from dtype('<U32') to dtype('float64') according to the rule 'safe'
        pytest.skip("FIAT python does currently not work on Linux..")

    # specify in- and output
    fiat_cfg = Path(
        fiat_sim_model,
        "settings.toml",
    )
    # Setup the method
    rule = FIATRun(fiat_cfg=fiat_cfg, fiat_exe=fiat_exe, run_method=method)
    rule.run_with_checks()
