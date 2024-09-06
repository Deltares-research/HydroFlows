from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import xarray as xr

from hydroflows.methods.validation import FloodmarksValidation


@pytest.fixture()
def hazard_map_data(rio_region: Path) -> xr.DataArray:
    # Get extent sfincs model
    geom = gpd.read_file(rio_region).to_crs(4326)
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
def hazard_map(tmp_path: Path, hazard_map_data: xr.DataArray) -> Path:
    # Set root
    root = Path(tmp_path, "hazard_map_output.tif")
    hazard_map_data.rio.set_crs("EPSG:4326", inplace=True)

    # Save the DataArray to a GeoTIFF file
    hazard_map_data.rio.to_raster(root)
    return root


def test_floodmarks_validation(
    tmp_path: Path, tmp_floodmark_points: Path, hazard_map: Path, rio_region: Path
):
    out_root = Path(tmp_path / "data")

    rule = FloodmarksValidation(
        floodmarks_geom=tmp_floodmark_points,
        region=rio_region,
        flood_hazard_map=hazard_map,
        waterlevel_prop="water_level_obs",
        scores_root=out_root,
    )

    assert (
        rule.output.validation_scores_csv
        == out_root / "validation_scores_floodmarks.csv"
    )
    rule.run_with_checks()
