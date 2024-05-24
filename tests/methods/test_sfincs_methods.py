import platform
import shutil
from pathlib import Path
from typing import Optional

import pytest

from hydroflows.methods import SfincsBuild, SfincsPostprocess, SfincsUpdateForcing
from hydroflows.methods.sfincs.sfincs_run import SfincsRun

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


def test_sfincs_build(rio_region, rio_test_data, tmp_path):
    input = {"region": str(rio_region)}

    sfincs_inp = Path(tmp_path, "model", "sfincs.inp")
    sfincs_region = Path(tmp_path, "model", "gis", "region.geojson")
    output = {"sfincs_inp": str(sfincs_inp), "sfincs_region": str(sfincs_region)}
    params = {"data_libs": str(rio_test_data), "res": 100.0, "river_upa": 10.0}
    SfincsBuild(input=input, output=output, params=params).run()
    assert sfincs_inp.exists()
    assert sfincs_region.exists()


def test_sfincs_update(rio_sfincs_model, tmp_path, test_data_dir):
    tmp_root = Path(tmp_path, "model")
    copy_tree(rio_sfincs_model.parent, tmp_root, max_level=0)
    sfincs_inp_event = Path(tmp_root, "event", "sfincs.inp")

    input = {
        "sfincs_inp": str(tmp_root / "sfincs.inp"),
        "event_catalog": str(test_data_dir / "events.yml"),
    }
    output = {"sfincs_inp": str(sfincs_inp_event)}
    params = {"event_name": "rp050"}

    SfincsUpdateForcing(input=input, output=output, params=params).run()

    assert sfincs_inp_event.is_file()


@pytest.mark.skipif(not SFINCS_EXE.exists(), reason="sfincs executable not found")
@pytest.mark.skipif(platform.system() != "Windows", reason="only supported on Windows")
def test_sfincs_run(rio_sfincs_model, tmp_path):
    tmp_root = Path(tmp_path, "model")
    copy_tree(rio_sfincs_model.parent, tmp_root, ignore=["gis", "subgrid"])
    sfincs_inp = Path(tmp_root, "sfincs.inp")
    sfincs_map = Path(sfincs_inp.parent, "sfincs_map.nc")
    assert sfincs_inp.is_file()

    input = {"sfincs_inp": str(sfincs_inp)}
    output = {"sfincs_map": str(sfincs_map)}
    params = {"sfincs_exe": str(SFINCS_EXE)}

    SfincsRun(input=input, output=output, params=params).run()

    assert sfincs_map.is_file()


def test_sfincs_postprocess(rio_sfincs_model, tmp_path):
    tmp_root = Path(tmp_path, "model")
    copy_tree(rio_sfincs_model.parent, tmp_root, ignore=["gis"])

    fn_sfincs_event_inp = Path(tmp_path, "model", "sfincs.inp")
    fn_sfincs_dep = Path(tmp_path, "model", "subgrid", "dep_subgrid.tif")
    fn_sfincs_inun_tif = Path(tmp_path, "model", "event.tif")

    input = {
        "sfincs_inp": str(fn_sfincs_event_inp),
        "sfincs_dep": str(fn_sfincs_dep),
    }
    output = {"sfincs_inun": str(fn_sfincs_inun_tif)}

    SfincsPostprocess(input=input, output=output).run()

    assert fn_sfincs_inun_tif.is_file()
