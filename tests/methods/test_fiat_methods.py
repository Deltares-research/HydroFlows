"""Testing for FIAT rules."""

import os
import platform
from pathlib import Path

import geopandas as gpd
import hydromt_fiat
import numpy as np
import pytest
import xarray as xr
from hydromt_fiat.fiat import FiatModel

from hydroflows.methods.fiat import FIATBuild, FIATRun, FIATUpdateHazard

FIAT_DATA_PATH = Path(
    os.path.dirname(hydromt_fiat.__file__),
    "data",
    "hydromt_fiat_catalog_global.yml",
).as_posix()


@pytest.fixture()
def fiat_simple_root(tmp_path: Path, sfincs_region_path):
    root = Path(tmp_path, "fiat_simple_model")

    model = FiatModel(
        root=root,
        mode="w+",
        data_libs=[
            FIAT_DATA_PATH,
            "artifact_data",
        ],
    )
    region_gdf = gpd.read_file(sfincs_region_path).to_crs(4326)
    model.setup_region({"geom": region_gdf})
    model.setup_output()
    model.setup_vulnerability(
        vulnerability_fn="jrc_vulnerability_curves",
        vulnerability_identifiers_and_linking_fn="jrc_vulnerability_curves_linking",
        unit="m",
        continent="europe",
    )
    model.setup_exposure_buildings(
        asset_locations="OSM",
        occupancy_type="OSM",
        max_potential_damage="jrc_damage_values",
        ground_floor_height=0,
        unit="m",
        extraction_method="centroid",
        damage_types=["structure", "content"],
        country="Italy",
    )
    model.write()
    return root


@pytest.fixture()
def hazard_map_data(sfincs_region_path: Path) -> xr.DataArray:
    # Get extent sfincs model
    geom = gpd.read_file(sfincs_region_path).to_crs(4326)
    bbox = list(geom.bounds.loc[0])

    # Make coordinates for hazard map
    lons = np.linspace(bbox[0], bbox[2], 5)
    lats = np.linspace(bbox[3], bbox[1], 5)

    data = np.ones([len(lats), len(lons)])
    da = xr.DataArray(data, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])
    da.name = "flood_map"
    da.raster.set_crs(4326)
    # da.raster.set_nodata(nodata=-9999.)
    da = da.raster.gdal_compliant()
    return da


@pytest.fixture()
def first_hazard_map(tmp_path: Path, hazard_map_data: xr.DataArray) -> Path:
    # Set root
    root = Path(tmp_path, "flood_map_rp010.nc")
    hazard_map_data.to_netcdf(root)
    return root


@pytest.fixture()
def second_hazard_map(tmp_path: Path, hazard_map_data: xr.DataArray) -> Path:
    # Set root
    root = Path(tmp_path, "flood_map_rp050.nc")
    (hazard_map_data * 2).to_netcdf(root)
    return root


def test_fiat_build(tmp_path: Path, sfincs_region_path: Path):
    # Setting input data
    region = sfincs_region_path.as_posix()
    fiat_root = Path(tmp_path, "fiat_model")

    # Setup the rule
    rule = FIATBuild(region=region, fiat_root=fiat_root)
    rule.run_with_checks()


def test_fiat_update_hazard(
    fiat_simple_root: Path,
    first_hazard_map: Path,
    second_hazard_map: Path,
    event_set_file: Path,
):
    # Specify in- and output
    fiat_cfg = Path(fiat_simple_root) / "settings.toml"
    # Setup the method.
    rule = FIATUpdateHazard(
        fiat_cfg=fiat_cfg,
        event_set_yaml=event_set_file,
        hazard_maps=[first_hazard_map, second_hazard_map],
    )
    rule.run_with_checks()


@pytest.mark.parametrize("method", ["python", "exe"])
def test_fiat_run(fiat_sim_tmp_root: Path, method: str, fiat_exe: Path, has_fiat_python: bool):
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
    fiat_cfg = Path(fiat_sim_tmp_root, "settings.toml")
    # Setup the method
    rule = FIATRun(fiat_cfg=fiat_cfg, fiat_exe=fiat_exe, run_method=method)
    rule.run_with_checks()