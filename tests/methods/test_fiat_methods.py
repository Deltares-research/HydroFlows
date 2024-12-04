"""Testing for FIAT rules."""

import platform
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import xarray as xr

from hydroflows.methods.fiat import FIATBuild, FIATRun, FIATUpdateHazard

FIAT_EXE = Path(
    Path(__file__).parent.parent,
    "_bin",
    "fiat",
    "fiat.exe",
)


@pytest.fixture()
def hazard_map_data(sfincs_test_region: Path) -> xr.DataArray:
    # Get extent sfincs model
    geom = gpd.read_file(sfincs_test_region).to_crs(4326)
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


def test_fiat_build(tmp_path: Path, sfincs_test_region: Path, build_cfgs: dict):
    # Setting input data
    region = sfincs_test_region.as_posix()
    fiat_root = Path(tmp_path, "fiat_model")

    # Setup the rule
    rule = FIATBuild(
        region=region, config=build_cfgs["fiat_build"], fiat_root=fiat_root
    )
    rule.run_with_checks()


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


# TODO add the hazard data.
@pytest.mark.skipif(not FIAT_EXE.exists(), reason="fiat executable not found")
@pytest.mark.skipif(platform.system() != "Windows", reason="only supported on Windows")
def test_fiat_run(fiat_tmp_model: Path):
    # specify in- and output
    fiat_cfg = Path(
        fiat_tmp_model,
        "simulations",
        "fluvial_events",
        "settings.toml",
    )
    # Setup the method
    rule = FIATRun(fiat_cfg=fiat_cfg, fiat_bin=FIAT_EXE)
    rule.run_with_checks()
