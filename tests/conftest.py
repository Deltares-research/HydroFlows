# fixtures with input and output files and folders
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
import rasterio.transform
import xarray as xr
from shapely.geometry import Point, Polygon

from hydroflows.cfg import CFG_DIR
from hydroflows.events import EventSet
from hydroflows.utils.example_data import fetch_data

EXAMPLE_DIR = Path(Path(__file__).parents[1], "examples")


## Genaral directories and files
@pytest.fixture(scope="session")
def build_cfgs() -> dict:
    """Return a dictonary of the build yaml's."""
    cfgs = {}
    for f in CFG_DIR.iterdir():
        cfgs[f.stem] = f
    return cfgs


@pytest.fixture(scope="session")
def example_data_dir() -> Path:
    """Return the path to the example data directory."""
    return Path(EXAMPLE_DIR, "data")


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the path to the testdata directory."""
    return Path(__file__).parent / "_data"


@pytest.fixture()
def event_set_file(test_data_dir) -> Path:
    """Return the path to the event set yaml."""
    return test_data_dir / "events.yml"


@pytest.fixture()
def event_set(event_set_file) -> EventSet:
    """Return event set."""
    return EventSet.from_yaml(event_set_file)


@pytest.fixture(scope="session")
def region():
    """Path to the region vector file."""
    path = EXAMPLE_DIR / "data" / "build" / "region.geojson"
    assert path.is_file()
    return path


@pytest.fixture(scope="session")
def global_data() -> Path:
    """Return path to global data directory."""
    path = fetch_data("global-data")
    assert Path(path, "data_catalog.yml").is_file()
    return path


@pytest.fixture(scope="session")
def global_catalog(global_data: Path) -> Path:
    """Return path to data catalog of global data."""
    return global_data / "data_catalog.yml"


## The cached and temporary models
@pytest.fixture(scope="session")
def fiat_test_model() -> Path:
    """Return path to the cached fiat model."""
    path = fetch_data("fiat-model")
    assert Path(path, "settings.toml")
    return path


@pytest.fixture()
def fiat_tmp_model(tmp_path: Path, fiat_test_model: Path) -> Path:
    """Return the path fiat model in temp directory."""
    tmp_root = tmp_path / "fiat_test_model"
    shutil.copytree(fiat_test_model, tmp_root)
    assert Path(tmp_root, "settings.toml").is_file()
    return tmp_root


@pytest.fixture(scope="session")
def wflow_test_model() -> Path:
    """Return the path to cached wflow model."""
    path = fetch_data("wflow-model")
    assert Path(path, "wflow_sbm.toml").is_file()
    return path


@pytest.fixture(scope="session")
def sfincs_test_model() -> Path:
    """Return the path to cached sfincs model."""
    path = fetch_data("sfincs-model")
    assert Path(path, "sfincs.inp").is_file()
    return path


@pytest.fixture(scope="session")
def sfincs_test_region(sfincs_test_model: Path):
    """Return the path to the pre-made sfincs region vector file."""
    path = sfincs_test_model / "gis" / "region.geojson"
    assert path.is_file()
    return path


@pytest.fixture()
def sfincs_tmp_model(tmp_path: Path, sfincs_test_model: Path) -> Path:
    """Return the path sfincs model in temp directory."""
    tmp_root = tmp_path / "sfincs_test_model"
    shutil.copytree(sfincs_test_model, tmp_root)
    assert Path(tmp_root, "sfincs.inp").is_file()
    return tmp_root


@pytest.fixture()
def gpex_data(global_data: Path) -> Path:
    """Return the path to the GPEX data."""
    gpex_file = global_data / "gpex.nc"
    assert gpex_file.is_file()
    return gpex_file


## Some files made on the fly
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
