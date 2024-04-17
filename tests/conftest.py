# fixtures with input and output files and folders

import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from shapely.geometry import Point, Polygon

from hydroflows.workflows.events import EventCatalog


@pytest.fixture()
def tmp_csv(tmpdir):
    """Create a temporary csv file."""
    csv_file = tmpdir.join("file.csv")
    csv_file.write("")
    return csv_file

@pytest.fixture()
def tmp_geojson(tmpdir):
    """Create a temporary GeoJSON file."""
    geojson_file = tmpdir.join("file.geojson")
    ids = ["id_1", "id_2", "id_3"]
    xs = [0, 1, 2]
    ys = [0, 1, 2]
    sizes = [10, 20, 30]  # Size of the polygons (in meters)


    # Create a GeoDataFrame from the data
    polygons = []
    for x, y, size in zip(xs, ys, sizes):
        half_size = size / 2
        vertices = [
            (x - half_size, y - half_size),
            (x + half_size, y - half_size),
            (x + half_size, y + half_size),
            (x - half_size, y + half_size),
            (x - half_size, y - half_size)  # Close the polygon
        ]
        polygon = Polygon(vertices)
        polygons.append(polygon)

    gdf = gpd.GeoDataFrame(
        {"ID": ids},
        geometry=polygons,
        crs='EPSG:32735'  # somewhere over southern africa
    )

    # Write the GeoDataFrame to a GeoJSON file
    gdf.to_file(geojson_file, driver='GeoJSON')
    return geojson_file




@pytest.fixture()
def tmp_tif(tmpdir):
    """Create a temporary tif file."""
    tif_file = tmpdir.join("file.tif")

    # Define some parameters
    width = 100
    height = 100
    dtype = np.uint8
    crs = 'EPSG:4326'  # WGS84 coordinate reference system
    transform = rasterio.transform.from_origin(0, 0, 0.01, 0.01) # some random transform

    # Generate some random data
    data = np.random.randint(0, 255, (height, width), dtype=dtype)

    # Write the data to a GeoTIFF file
    with rasterio.open(
        str(tif_file), 'w', driver='GTiff',
        width=width, height=height, count=1,
        dtype=dtype, crs=crs, transform=transform
    ) as dst:
        dst.write(data, 1)
    # dst.close()
    return tif_file


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    return Path(__file__).parent / "_data"


@pytest.fixture()
def event_catalog(test_data_dir) -> EventCatalog:
    return EventCatalog.from_yaml(test_data_dir / "events.yml")


@pytest.fixture()
def sfincs_region():
    return gpd.GeoDataFrame(
        geometry=[
            Polygon(
                [
                    [318650.0, 5040000.0],
                    [316221.0, 5044767.0],
                    [327359.0, 5050442.0],
                    [329788.0, 5045675.0],
                    [318650.0, 5040000.0],
                ]
            )
        ],
        crs="EPSG:32633",
    )


@pytest.fixture()
def sfincs_region_path(tmpdir, sfincs_region):
    p = Path(str(tmpdir), "region.geojson")
    sfincs_region.to_file(p)
    return p


@pytest.fixture()
def sfincs_src_points():
    return gpd.GeoDataFrame(
        geometry=[
            Point(282937.059, 5079303.114),
        ],
        crs="EPSG:32633",
    )

@pytest.fixture(scope="function")  # noqa: PT003
def sfincs_tmp_model_root(test_data_dir, tmpdir):
    """Return a temporary directory with a copy of the sfincs model."""
    # copy the sfincs model to a temporary directory
    sfincs_model_root_tmp = tmpdir / "sfincs_model"
    # copy
    sfincs_model_root = test_data_dir / "sfincs_model"
    shutil.copytree(sfincs_model_root, sfincs_model_root_tmp)
    return sfincs_model_root_tmp
