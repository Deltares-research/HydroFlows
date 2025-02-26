# fixtures with input and output files and folders
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

import geopandas as gpd
import hydromt  # noqa: F401
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import Point

from hydroflows.cfg import CFG_DIR
from hydroflows.methods.wflow.scripts import SCRIPTS_DIR
from hydroflows.utils.example_data import fetch_data

EXAMPLE_DIR = Path(Path(__file__).parents[2], "examples")


## The executables of the models
@pytest.fixture(scope="session")
def has_docker():
    try:
        return subprocess.run(["docker", "stats", "--no-stream"]).returncode == 0
    except FileNotFoundError:
        return False


@pytest.fixture(scope="session")
def has_apptainer():
    try:
        return subprocess.run(["apptainer", "version"]).returncode == 0
    except FileNotFoundError:
        return False


@pytest.fixture(scope="session")
def has_wflow_julia():
    try:
        return subprocess.run(["julia", "-e", "using Wflow"]).returncode == 0
    except FileNotFoundError:
        return False


@pytest.fixture(scope="session")
def has_fiat_python():
    try:
        import fiat  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.fixture(scope="session")
def sfincs_exe():
    return Path(EXAMPLE_DIR, "bin", "sfincs_v2.1.1", "sfincs.exe")


@pytest.fixture(scope="session")
def wflow_exe():
    return Path(EXAMPLE_DIR, "bin", "wflow_v0.8.1", "bin", "wflow_cli.exe")


@pytest.fixture(scope="session")
def fiat_exe():
    return Path(EXAMPLE_DIR, "bin", "fiat_v0.2.1", "fiat.exe")


## Genaral directories and files
@pytest.fixture(scope="session")
def build_cfgs() -> dict:
    """Return a dictonary of the build yaml's."""
    cfgs = {}
    for f in CFG_DIR.iterdir():
        cfgs[f.stem] = f
    return cfgs


@pytest.fixture(scope="session")
def region(global_data):
    """Path to the region vector file."""
    path = global_data / "region.geojson"
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


@pytest.fixture(scope="session")
def cmip6_data() -> Path:
    """Return the path to the cmip6 data directory."""
    path = fetch_data("cmip6-data")
    assert Path(path, "data_catalog.yml").is_file()
    return path


@pytest.fixture(scope="session")
def cmip6_catalog(cmip6_data: Path):
    """Return path to data catalog of cmip6 data."""
    return cmip6_data / "data_catalog.yml"


@pytest.fixture(scope="session")
def cmip6_stats() -> Path:
    path = fetch_data("cmip6-stats")
    assert Path(path, "climatology").is_dir()
    assert Path(path, "change_factor").is_dir()
    assert Path(
        path, "climatology", "climatology_NOAA-GFDL_GFDL-ESM4_historical.nc"
    ).is_file()
    return path


@pytest.fixture(scope="session")
def merit_hydro_basins(global_data: Path) -> Path:
    """Return the path to the merit hydro basin."""
    merit_file = global_data / "cat_MERIT_Hydro_v07_Basins_v01.gpkg"
    assert merit_file.is_file()
    return merit_file


## The cached and temporary models
@pytest.fixture(scope="session")
def fiat_cached_model() -> Path:
    """Return path to the cached fiat model."""
    path = fetch_data("fiat-model")
    assert Path(path, "settings.toml")
    return path


@pytest.fixture()
def fiat_tmp_model(tmp_path: Path, fiat_cached_model: Path) -> Path:
    """Return the path of the fiat model in temp directory."""
    tmp_root = tmp_path / "fiat_tmp_model"
    ignore = shutil.ignore_patterns("simulations", "*.tar.gz")
    shutil.copytree(fiat_cached_model, tmp_root, ignore=ignore)
    assert Path(tmp_root, "settings.toml").is_file()
    return tmp_root


@pytest.fixture()
def fiat_sim_model(fiat_cached_model: Path, fiat_tmp_model: Path):
    """Return the path of the temporary fiat model for simulations."""
    sim_dir = "simulations/fluvial_events"
    sim_root = fiat_tmp_model / sim_dir
    ignore = shutil.ignore_patterns("output")
    shutil.copytree(fiat_cached_model / sim_dir, sim_root, ignore=ignore)
    assert Path(sim_root, "settings.toml").is_file()
    return sim_root


@pytest.fixture(scope="session")
def sfincs_cached_model() -> Path:
    """Return the path to cached sfincs model."""
    path = fetch_data("sfincs-model")
    assert Path(path, "sfincs.inp").is_file()
    return path


@pytest.fixture()
def sfincs_tmp_model(tmp_path: Path, sfincs_cached_model: Path) -> Path:
    """Return the path sfincs model in temp directory."""
    tmp_root = tmp_path / "sfincs_tmp_model"
    ignore = shutil.ignore_patterns("simulations", "*.tar.gz")
    shutil.copytree(sfincs_cached_model, tmp_root, ignore=ignore)
    assert Path(tmp_root, "sfincs.inp").is_file()
    return tmp_root


@pytest.fixture()
def sfincs_sim_model(sfincs_cached_model: Path, sfincs_tmp_model: Path) -> Path:
    """Return the path to the sfincs test model nested simulation."""
    sim_dir = "simulations/p_event01"
    sim_root = sfincs_tmp_model / sim_dir
    shutil.copytree(sfincs_cached_model / sim_dir, sim_root)
    assert Path(sim_root, "sfincs.inp").is_file()
    return sim_root


@pytest.fixture(scope="session")
def sfincs_test_region(sfincs_cached_model):
    """Return the path to the pre-made sfincs region vector file."""
    path = sfincs_cached_model / "gis" / "region.geojson"
    assert path.is_file()
    return path


@pytest.fixture(scope="session")
def wflow_cached_model() -> Path:
    """Return the path to cached wflow model."""
    path = fetch_data("wflow-model")
    assert Path(path, "wflow_sbm.toml").is_file()
    return path


@pytest.fixture()
def wflow_tmp_model(tmp_path: Path, wflow_cached_model: Path) -> Path:
    """Return the path to the temporary wflow model for testing."""
    tmp_root = tmp_path / "wflow_tmp_model"
    ignore = shutil.ignore_patterns("simulations", "*.tar.gz")
    shutil.copytree(wflow_cached_model, tmp_root, ignore=ignore)
    assert Path(tmp_root, "wflow_sbm.toml").is_file()
    return tmp_root


@pytest.fixture()
def wflow_sim_model(wflow_cached_model: Path, wflow_tmp_model: Path) -> Path:
    """Return the path to the wflow test model nested simulation."""
    sim_dir = "simulations/default"
    sim_root = wflow_tmp_model / sim_dir
    ignore = shutil.ignore_patterns("run_default")
    shutil.copytree(wflow_cached_model / sim_dir, sim_root, ignore=ignore)
    assert Path(sim_root, "wflow_sbm.toml").is_file()
    return sim_root


@pytest.fixture
def wflow_run_script():
    """Return path to the julia script."""
    p = Path(SCRIPTS_DIR, "run_wflow.jl")
    assert p.is_file()
    return p


@pytest.fixture()
def gpex_data(global_data: Path) -> Path:
    """Return the path to the GPEX data."""
    gpex_file = global_data / "gpex.nc"
    assert gpex_file.is_file()
    return gpex_file


## Some files made on the fly
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
def hazard_map_tif(tmp_path: Path, hazard_map_data: xr.DataArray) -> Path:
    # Set root
    root = Path(tmp_path, "hazard_map.tif")
    hazard_map_data.raster.set_crs("EPSG:4326")

    # Save the DataArray to a GeoTIFF file
    hazard_map_data.raster.to_raster(root)
    return root


@pytest.fixture()
def tmp_precip_time_series_nc(tmp_path: Path) -> Path:
    # Generating datetime index
    dates = pd.date_range(start="2001-01-01", end="2009-12-31", freq="h")

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

    fn_time_series_nc = Path(tmp_path, "precip_output_scalar.nc")
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

    fn_time_series_nc = Path(tmp_path, "discharge_output_scalar.nc")
    da.to_netcdf(fn_time_series_nc)

    return fn_time_series_nc


@pytest.fixture()
def tmp_floodmark_points(tmp_path: Path) -> Path:
    """Create a temporary GeoJSON file."""
    geojson_file = tmp_path / "floodmarks.geojson"

    # locations for livenza area
    data = {
        "water_level_obs": [1.5, 2.7, 1.1],
        "geometry": [
            Point(12.842475, 45.605216),
            Point(
                12.865855,
                45.603384,
            ),
            Point(
                12.885014,
                45.618822,
            ),  # outside
        ],
    }

    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    gdf.to_file(geojson_file, driver="GeoJSON")

    return geojson_file


@pytest.fixture()
def temp_waterlevel_timeseries_nc(tmp_path: Path) -> Path:
    dates = pd.date_range(start="2000-01-01", end="2015-12-31", freq="10min")

    np.random.seed(1234)
    data = np.random.rand(len(dates), 1)

    da = xr.DataArray(
        data=data,
        dims=("time", "stations"),
        coords={"time": dates, "stations": ["1"]},
    )

    da.name = "h"

    fn_time_series_nc = Path(tmp_path, "water_level_output_scalar.nc")
    da.to_netcdf(fn_time_series_nc)

    return fn_time_series_nc


@pytest.fixture()
def tide_surge_timeseries() -> Tuple[xr.DataArray, xr.DataArray]:
    dates = pd.date_range(start="2000-01-01", end="2005-12-31", freq="10min")

    np.random.seed(1234)
    data1 = np.random.rand(len(dates))
    np.random.seed(5678)
    data2 = np.random.rand(len(dates))

    t = xr.DataArray(data=data1, dims=("time"), coords={"time": dates}, name="t")
    s = xr.DataArray(data=data2, dims=("time"), coords={"time": dates}, name="s")
    t = t.expand_dims(dim={"stations": 1})
    s = s.expand_dims(dim={"stations": 1})
    return t, s


@pytest.fixture()
def waterlevel_rps() -> xr.Dataset:
    rps = xr.Dataset(
        coords=dict(rps=("rps", [1, 10, 100])),
        data_vars=dict(return_values=(["rps"], np.array([0.5, 1, 1.5]))),
    )
    rps = rps.expand_dims(dim={"stations": 1})
    return rps


@pytest.fixture()
def bnd_locations() -> gpd.GeoDataFrame:
    bnds = gpd.GeoDataFrame(data={"stations": [1]}, geometry=[Point(1, 1)], crs=4326)
    return bnds
