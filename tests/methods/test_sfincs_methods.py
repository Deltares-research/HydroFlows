import datetime
import platform
from pathlib import Path

import pytest
from hydromt_sfincs import SfincsModel

from hydroflows.events import Event
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsDownscale,
    SfincsRegion,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.methods.sfincs.sfincs_utils import parse_event_sfincs


@pytest.mark.requires_test_data()
def test_sfincs_region(
    sfincs_test_region: Path, merit_hydro_basins: Path, tmp_path: Path
):
    sfincs_region = SfincsRegion(
        aoi=str(sfincs_test_region),
        subbasins=str(merit_hydro_basins),
        sfincs_region=Path(tmp_path, "data", "sfincs_region.geojson"),
    )

    sfincs_region.run_with_checks()


@pytest.mark.requires_test_data()
def test_sfincs_build(
    region: Path, build_cfgs: dict, global_catalog: Path, tmp_path: Path
):
    sfincs_root = Path(tmp_path, "model")
    sfincs_build = SfincsBuild(
        region=str(region),
        config=build_cfgs["sfincs_build"],
        sfincs_root=str(sfincs_root),
        catalog_path=str(global_catalog),
    )
    assert sfincs_build.output.sfincs_inp == sfincs_root / "sfincs.inp"

    sfincs_build.run_with_checks()


@pytest.mark.requires_test_data()
@pytest.mark.parametrize("copy_model", [True, False])
def test_sfincs_update(sfincs_tmp_model: Path, event_set_file: Path, copy_model: bool):
    event_name = "p_event01"
    event_yml = event_set_file.parent / f"{event_name}.yml"
    if copy_model:
        output_dir = sfincs_tmp_model.parent / "sim"
    else:
        output_dir = sfincs_tmp_model / "sim"
    sf = SfincsUpdateForcing(
        sfincs_inp=str(sfincs_tmp_model / "sfincs.inp"),
        event_yaml=event_yml.as_posix(),
        event_name=event_name,
        output_dir=output_dir,
        copy_model=copy_model,
    )
    assert sf.output.sfincs_out_inp == sf.params.output_dir / event_name / "sfincs.inp"
    sf.run_with_checks()


@pytest.mark.requires_test_data()
@pytest.mark.parametrize("sfincs_root", ["sfincs_tmp_model", "sfincs_sim_model"])
@pytest.mark.parametrize("method", ["docker", "exe", "apptainer"])
def test_sfincs_run(
    sfincs_root: Path,
    method: str,
    has_docker: bool,
    has_apptainer: bool,
    sfincs_exe: Path,
    request,
):
    if method == "docker" and not has_docker:
        pytest.skip("Docker not available")
    elif method == "apptainer" and not has_apptainer:
        pytest.skip("Apptainer not available")
    elif method == "exe" and not sfincs_exe.is_file():
        pytest.skip(f"SFINCS executable not found at {sfincs_exe}")
    elif method == "exe" and platform.system() != "Windows":
        pytest.skip("SFINCS exe only supported on Windows")
    # load fixture
    sfincs_root: Path = request.getfixturevalue(sfincs_root)

    sfincs_inp = Path(sfincs_root, "sfincs.inp")
    sfincs_map = Path(sfincs_inp.parent, "sfincs_map.nc")
    sfincs_log = Path(sfincs_inp.parent, "sfincs.log")
    if sfincs_map.is_file():
        sfincs_map.unlink()
    if sfincs_log.is_file():
        sfincs_log.unlink()

    # modify the tstop to a short time
    sf = SfincsModel(root=sfincs_root, mode="r+")
    sf.set_config("tref", "20191231 000000")
    sf.set_config("tstart", "20191231 000000")
    sf.set_config("tstop", "20191231 010000")
    sf.write_config()

    assert sfincs_inp.is_file()
    sf_run = SfincsRun(
        sfincs_inp=str(sfincs_inp), run_method=method, sfincs_exe=sfincs_exe
    )
    assert sf_run.output.sfincs_map == sfincs_map
    sf_run.run_with_checks()


@pytest.mark.requires_test_data()
def test_sfincs_downscale(sfincs_tmp_model: Path, sfincs_sim_model: Path):
    tmp_hazard_root = Path(sfincs_tmp_model, "hazard")

    sf_post = SfincsDownscale(
        sfincs_map=str(sfincs_sim_model / "sfincs_map.nc"),
        sfincs_subgrid_dep=str(sfincs_tmp_model / "subgrid" / "dep_subgrid.tif"),
        output_root=str(tmp_hazard_root),
        event_name="test",
    )
    assert sf_post.output.hazard_tif == tmp_hazard_root / "hmax_test.tif"

    sf_post.run_with_checks()


@pytest.mark.requires_test_data()
def test_parse_event_sfincs(sfincs_tmp_model: Path, tmp_path: Path):
    # get dummy location within the model domain
    # read gis/region.geojson
    sf = SfincsModel(root=sfincs_tmp_model, mode="r")
    sf.read()
    # create dummy bnd points
    sf.setup_waterlevel_bnd_from_mask(merge=False)
    gdf_bnd = sf.forcing["bzs"].vector.to_gdf().iloc[[0]].reset_index()
    gdf_bnd["index"] = 1
    tmp_bnd = Path(tmp_path, "bzs.geojson")
    gdf_bnd.to_file(tmp_bnd, driver="GeoJSON")
    # create dummy scr points
    if "dis" in sf.forcing:
        gdf_src = sf.forcing["dis"].vector.to_gdf().iloc[[0]].reset_index()
        gdf_src["index"] = 1
        tmp_src = Path(tmp_path, "dis.geojson")
        gdf_src.to_file(tmp_src, driver="GeoJSON")
    else:
        tmp_src = tmp_bnd

    # create a tmp time series file
    tmp_csv = Path(tmp_path, "timeseries.csv")
    with open(tmp_csv, "w") as f:
        f.write("time,1\n2020-01-01,1.0\n2020-01-02,1.0\n")

    # create a dummy event
    event = Event(
        name="test",
        forcings=[
            {
                "type": "water_level",
                "path": tmp_csv,
                "scale_mult": 2.0,
                "locs_path": tmp_bnd,
            },
            {
                "type": "rainfall",
                "path": tmp_csv,
                "scale_add": 2.0,
            },
            {
                "type": "discharge",
                "path": tmp_csv,
                "locs_path": tmp_src,
            },
        ],
    )

    parse_event_sfincs(
        root=sfincs_tmp_model, event=event, out_root=sfincs_tmp_model / "sim" / "test"
    )

    sf = SfincsModel(root=sfincs_tmp_model / "sim" / "test", mode="r")
    sf.read()
    assert sf.config["tstart"] == datetime.datetime(2020, 1, 1, 0, 0)
    assert (sf.forcing["bzs"].index.values == 1).all()
    assert (sf.forcing["bzs"].values == 2).all()
    assert (sf.forcing["precip"].values == 3).all()
    assert (sf.forcing["dis"].values == 1).all()
