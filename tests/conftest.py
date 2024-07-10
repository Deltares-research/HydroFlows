# fixtures with input and output files and folders
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pooch
import pytest
import rasterio
from requests import HTTPError
from shapely.geometry import Point, Polygon

from hydroflows.events import EventCatalog


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    return Path(__file__).parent / "_data"


@pytest.fixture(scope="session")
def large_test_data() -> pooch.Pooch:
    """Return a pooch for large test test data."""
    path = Path(__file__).parent / "_large_data"
    try:  # get registry from remote
        base_url = r"https://github.com/Deltares-research/hydroflows-data/releases/download/data"
        registry_file = pooch.retrieve(
            url=f"{base_url}/registry.txt",
            known_hash=None,
            path=path,
            fname="registry.txt",
        )
    except HTTPError:  # use cached registry
        base_url = str(path / "data")
        registry_file = path / "registry.txt"
    if not Path(registry_file).is_file():
        raise FileNotFoundError(f"Registry file not found: {registry_file}")
    # create a Pooch instance for the large test data
    large_test_data = pooch.create(
        path=path / "data",
        base_url=base_url,
        registry=None,
    )
    large_test_data.load_registry(path / "registry.txt")
    return large_test_data


@pytest.fixture(scope="session")
def rio_test_data(large_test_data: pooch.Pooch) -> Path:
    """Return the path to the rio data catalog."""
    paths = large_test_data.fetch(
        "rio_data_catalog.zip",
        processor=pooch.Unzip(extract_dir="rio_data_catalog"),
    )
    path = Path(paths[0]).parent / "data_catalog.yml"
    assert path.is_file()
    return path


@pytest.fixture(scope="session")
def rio_wflow_model(large_test_data: pooch.Pooch) -> Path:
    """Return the path to the rio wflow model config file."""
    _ = large_test_data.fetch(
        "rio_wflow_model.zip",
        processor=pooch.Unzip(extract_dir="rio_wflow_model"),
    )
    path = large_test_data.path / "rio_wflow_model" / "wflow.toml"
    assert path.is_file()
    return path


@pytest.fixture(scope="session")
def rio_sfincs_model(large_test_data: pooch.Pooch) -> Path:
    """Return the path to the rio data catalog."""
    _ = large_test_data.fetch(
        "rio_sfincs_model.zip",
        processor=pooch.Unzip(extract_dir="rio_sfincs_model"),
    )
    path = Path(large_test_data.path) / "rio_sfincs_model" / "sfincs.inp"
    assert path.is_file()
    return path


@pytest.fixture(scope="session")
def rio_region(test_data_dir) -> Path:
    return test_data_dir / "rio_region.geojson"


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
            (x - half_size, y - half_size),  # Close the polygon
        ]
        polygon = Polygon(vertices)
        polygons.append(polygon)

    gdf = gpd.GeoDataFrame(
        {"ID": ids},
        geometry=polygons,
        crs="EPSG:32735",  # somewhere over southern africa
    )

    # Write the GeoDataFrame to a GeoJSON file
    gdf.to_file(geojson_file, driver="GeoJSON")
    return geojson_file


@pytest.fixture()
def tmp_tif(tmpdir):
    """Create a temporary tif file."""
    tif_file = tmpdir.join("file.tif")

    # Define some parameters
    width = 100
    height = 100
    dtype = np.uint8
    crs = "EPSG:4326"  # WGS84 coordinate reference system
    transform = rasterio.transform.from_origin(
        0, 0, 0.01, 0.01
    )  # some random transform

    # Generate some random data
    data = np.random.randint(0, 255, (height, width), dtype=dtype)

    # Write the data to a GeoTIFF file
    with rasterio.open(
        str(tif_file),
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype=dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    # dst.close()
    return tif_file


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
