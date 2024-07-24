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

from hydroflows.methods import FIATBuild, FIATRun, FIATUpdateHazard

FIAT_DATA_PATH = Path(
    os.path.dirname(hydromt_fiat.__file__),
    "data",
    "hydromt_fiat_catalog_global.yml",
).as_posix()

FIAT_EXE = Path(
    Path(__file__).parent.parent,
    "_bin",
    "fiat",
    "fiat.exe",
)


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
def hazard_map_data(sfincs_region_path):
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
def first_hazard_map(tmp_path: Path, hazard_map_data):
    # Set root
    root = Path(tmp_path, "flood_map_rp010.nc")
    hazard_map_data.to_netcdf(root)
    return root


@pytest.fixture()
def second_hazard_map(tmp_path: Path, hazard_map_data):
    # Set root
    root = Path(tmp_path, "flood_map_rp050.nc")
    (hazard_map_data * 2).to_netcdf(root)
    return root


def test_fiat_build(tmp_path: Path, sfincs_region_path):
    # Setting input data
    region = sfincs_region_path.as_posix()
    fiat_root = Path(tmp_path, "fiat_model")

    # Setup the rule
    rule = FIATBuild(region=region, fiat_root=fiat_root)
    rule.run_with_checks()


def test_fiat_update_hazard(
    fiat_simple_root, first_hazard_map, second_hazard_map, event_set_file
):
    # Specify in- and output
    fiat_cfg = Path(fiat_simple_root) / "settings.toml"
    # Setup the method.
    rule = FIATUpdateHazard(
        fiat_cfg=fiat_cfg,
        event_set_yaml=event_set_file,
        hazard_maps=[first_hazard_map, second_hazard_map],
    )
    rule.run()

    # Assert that the hazard file exists
    assert rule.output.fiat_hazard.exists()


# @pytest.mark.skipif(not FIAT_EXE.exists(), reason="sfincs executable not found")
@pytest.mark.skipif(platform.system() != "Windows", reason="only supported on Windows")
def test_fiat_run(tmp_path: Path, fiat_simple_root: Path):
    # specify in- and output
    fiat_cfg = Path(fiat_simple_root) / "settings.toml"
    # Setup the method
    rule = FIATRun(fiat_cfg=fiat_cfg, fiat_bin=FIAT_EXE)
    rule.run()

    # Assert the output
    pass
