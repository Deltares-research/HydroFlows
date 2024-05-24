"""Testing for FIAT rules."""
import math
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
def fiat_simple_root(tmp_path, sfincs_region_path):
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
def simple_hazard_map(tmp_path, sfincs_region_path):
    # Set root
    root = Path(tmp_path, "flood_map.nc")
    # Get extent sfincs model
    geom = gpd.read_file(sfincs_region_path).to_crs(4326)
    bbox = list(geom.bounds.loc[0])

    # Make coordinates for hazard map
    lons = np.arange(math.floor(bbox[0]), math.ceil(bbox[2]) + 0.1, 0.25)
    lats = np.arange(math.ceil(bbox[3]), math.floor(bbox[1]) - 0.1, -0.25)
    data = np.ones([len(lats), len(lons)])
    da = xr.DataArray(data, coords={"lat": lats, "lon": lons}, dims=["lat", "lon"])
    da.name = "flood_map"
    da.raster.set_crs(4326)
    da = da.raster.gdal_compliant()
    da.to_netcdf(root)
    return root


def test_fiat_build(tmp_path, sfincs_region_path):
    # Setting input data
    input = {
        "region": sfincs_region_path.as_posix(),
    }
    fn_fiat_cfg = Path(tmp_path, "fiat_model", "settings.toml")
    output = {"fiat_cfg": fn_fiat_cfg}

    # Setup the rule
    rule = FIATBuild(input=input, output=output)
    rule.run()

    assert fn_fiat_cfg.exists()


def test_fiat_update_hazard(tmp_path, fiat_simple_root, simple_hazard_map):
    # Specify in- and output
    input = {
        "fiat_cfg": Path(fiat_simple_root, "settings.toml"),
        "hazard_map": simple_hazard_map,
    }
    output = {"fiat_haz": Path(fiat_simple_root, "hazard", "hazard_map.nc")}

    # Setup the method.
    rule = FIATUpdateHazard(input=input, output=output)
    rule.run()

    # Assert that the hazard file exists
    assert output["fiat_haz"].exists()


@pytest.mark.skipif(not FIAT_EXE.exists(), reason="sfincs executable not found")
@pytest.mark.skipif(platform.system() != "Windows", reason="only supported on Windows")
def test_fiat_run(tmp_path):
    # specify in- and output
    input = {}
    output = {}

    # Setup the method
    rule = FIATRun(input=input, output=output)
    rule.run()

    # Assert the output
    pass
