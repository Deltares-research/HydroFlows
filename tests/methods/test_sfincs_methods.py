import platform
import shutil
from pathlib import Path
from typing import Optional

import pytest
from hydromt_sfincs import SfincsModel

from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsPostprocess,
    SfincsRun,
    SfincsUpdateForcing,
)

SFINCS_EXE = Path(__file__).parent.parent / "_bin" / "sfincs" / "sfincs.exe"


def copy_tree(
    src: Path,
    dst: Path,
    ignore: Optional[list] = None,
    level: int = 0,
    max_level: int = 10,
):
    ignore = [] if ignore is None else ignore
    dst.mkdir(parents=True, exist_ok=True)
    for path in src.iterdir():
        if path.name in ignore:
            continue
        if path.is_file():
            shutil.copy2(path, dst / path.name)
        elif path.is_dir() and level < max_level:
            copy_tree(path, dst / path.name, ignore, level + 1, max_level)


@pytest.mark.requires_data()
def test_sfincs_build(rio_region: Path, rio_test_data: Path, tmp_path: Path):
    sfincs_root = Path(tmp_path, "model")
    sfincs_build = SfincsBuild(
        region=str(rio_region),
        sfincs_root=str(sfincs_root),
        res=100.0,
        river_upa=10.0,
        data_libs=str(rio_test_data),
    )
    assert sfincs_build.output.sfincs_inp == sfincs_root / "sfincs.inp"
    assert sfincs_build.params.river_upa == 10.0

    sfincs_build.run_with_checks()


@pytest.mark.requires_data()
def test_sfincs_update(rio_sfincs_model: Path, test_data_dir: Path, tmp_path: Path):
    tmp_root = Path(tmp_path, "model")
    copy_tree(rio_sfincs_model.parent, tmp_root, max_level=0)
    event_yaml = test_data_dir / "event_rp010.yml"

    sf = SfincsUpdateForcing(
        sfincs_inp=str(tmp_root / "sfincs.inp"),
        event_yaml=str(event_yaml),
        event_name="rp010",
        sim_subfolder="sim",
    )
    assert sf.output.sfincs_out_inp == tmp_root / "sim" / "rp010" / "sfincs.inp"
    sf.run_with_checks()


@pytest.mark.requires_data()
@pytest.mark.skipif(not SFINCS_EXE.exists(), reason="sfincs executable not found")
@pytest.mark.skipif(platform.system() != "Windows", reason="only supported on Windows")
def test_sfincs_run(rio_sfincs_model: Path, tmp_path: Path):
    tmp_root = Path(tmp_path, "model")
    copy_tree(rio_sfincs_model.parent, tmp_root, ignore=["gis", "subgrid"])
    sfincs_inp = Path(tmp_root, "sfincs.inp")
    sfincs_map = Path(sfincs_inp.parent, "sfincs_map.nc")

    # modify the tstop to a short time
    sf = SfincsModel(root=tmp_root, mode="r+")
    sf.set_config("tref", "20191231 000000")
    sf.set_config("tstart", "20191231 000000")
    sf.set_config("tstop", "20191231 010000")
    sf.write_config()

    assert sfincs_inp.is_file()
    sf_run = SfincsRun(sfincs_inp=str(sfincs_inp), sfincs_exe=SFINCS_EXE)
    assert sf_run.output.sfincs_map == sfincs_map
    sf_run.run_with_checks()


@pytest.mark.requires_data()
def test_sfincs_postprocess(rio_sfincs_model: Path, tmp_path: Path):
    tmp_root = Path(tmp_path, "model")
    copy_tree(rio_sfincs_model.parent, tmp_root, ignore=["gis"])
    tmp_hazard_root = Path(tmp_path, "hazard")

    sf_post = SfincsPostprocess(
        sfincs_map=str(tmp_root / "sfincs_map.nc"),
        sfincs_subgrid_dep=str(tmp_root / "subgrid" / "dep_subgrid.tif"),
        hazard_root=str(tmp_hazard_root),
        event_name="test",
    )
    assert sf_post.output.hazard_tif == tmp_hazard_root / "test.tif"

    sf_post.run_with_checks()
