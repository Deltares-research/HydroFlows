# fixtures with input and output files and folders
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pooch
import pytest
import rasterio
import rasterio.transform
import xarray as xr
from requests import HTTPError
from shapely.geometry import Point, Polygon

from hydroflows.events import EventSet


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
def tmp_merit_hydro_basins(example_data_dir: Path, tmp_path: Path) -> Path:
    """Return the path to the merit hydro basin."""
    # fetch("globa-data", output_dir=example_data_dir)
    cache_merit_file = Path(example_data_dir, "merit_hydro_basins.geojson")
    tmp_merit_file = Path(tmp_path, "merit_hydro_basins.geojson")
    shutil.copy(cache_merit_file, tmp_merit_file)
    return tmp_merit_file


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
def tmp_csv(tmp_path: Path) -> Path:
    """Create a temporary csv file."""
    csv_file = tmp_path / "file.csv"
    # create dummy timeseries data
    times = pd.date_range(start="2021-01-01", periods=10, freq="D")
    data = np.ones(len(times))
    df = pd.DataFrame(data, index=times, columns=["data"])
    # write to csv
    df.to_csv(csv_file)
    return csv_file


@pytest.fixture()
def tmp_precip_time_series_nc(tmp_path: Path) -> Path:
    # Generating datetime index
    dates = pd.date_range(start="2000-01-01", end="2009-12-31", freq="h")

    # set a seed for reproducibility
    np.random.seed(0)
    # Generating random rainfall data
    data = np.random.rand(len(dates))

    da = xr.DataArray(
        data,
        dims=("time"),
        coords={"time": dates},
        name="tp",
        attrs={"long_name": "Total precipitation", "units": "mm"},
    )

    fn_time_series_nc = Path(tmp_path, "output_scalar.nc")
    da.to_netcdf(fn_time_series_nc)

    return fn_time_series_nc


@pytest.fixture()
def tmp_disch_time_series_nc(tmp_path: Path) -> Path:
    rng = np.random.default_rng(12345)
    normal = pd.DataFrame(
        rng.random(size=(365 * 100, 2)) * 100,
        index=pd.date_range(start="2020-01-01", periods=365 * 100, freq="1D"),
    )
    ext = rng.gumbel(loc=100, scale=25, size=(200, 2))  # Create extremes
    for i in range(2):
        normal.loc[normal.nlargest(200, i).index, i] = ext[:, i].reshape(-1)
    da = xr.DataArray(
        data=normal.values,
        dims=("time", "Q_gauges"),
        coords={
            "time": pd.date_range(start="2000-01-01", periods=365 * 100, freq="D"),
            "Q_gauges": ["1", "2"],
        },
        attrs=dict(_FillValue=-9999),
    )

    da.name = "Q"

    fn_time_series_nc = Path(tmp_path, "output_scalar.nc")
    da.to_netcdf(fn_time_series_nc)

    return fn_time_series_nc


@pytest.fixture()
def tmp_geojson(tmp_path: Path) -> Path:
    """Create a temporary GeoJSON file."""
    geojson_file = tmp_path / "file.geojson"
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
def tmp_tif(tmp_path: Path) -> Path:
    """Create a temporary tif file."""
    tif_file = tmp_path / "file.tif"

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
def event_set_file(test_data_dir) -> Path:
    return test_data_dir / "events.yml"


@pytest.fixture()
def event_set(event_set_file) -> EventSet:
    return EventSet.from_yaml(event_set_file)


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
def sfincs_region_path(tmp_path: Path, sfincs_region: gpd.GeoDataFrame) -> Path:
    p = Path(tmp_path, "region.geojson")
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


@pytest.fixture()
def tmp_floodmark_points(tmp_path: Path) -> Path:
    """Create a temporary GeoJSON file."""
    geojson_file = tmp_path / "floodmarks.geojson"

    data = {
        "water_level_obs": [1.5, 2.7, 1.1],
        "geometry": [
            Point(-43.34287654946553, -22.832107208119936),
            Point(-43.2989472972867, -22.85036460253447),
            Point(-43.34590242111892, -22.856179585143337),
        ],
    }

    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    gdf.to_file(geojson_file, driver="GeoJSON")

    return geojson_file


@pytest.fixture(scope="function")  # noqa: PT003
def sfincs_tmp_model_root(test_data_dir, tmpdir):
    """Return a temporary directory with a copy of the sfincs model."""
    # copy the sfincs model to a temporary directory
    sfincs_model_root_tmp = tmpdir / "sfincs_model"
    # copy
    sfincs_model_root = test_data_dir / "sfincs_model"
    shutil.copytree(sfincs_model_root, sfincs_model_root_tmp)
    return sfincs_model_root_tmp
