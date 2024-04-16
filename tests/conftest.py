# fixtures with input and output files and folders

import shutil
from pathlib import Path

import geopandas as gpd
import pooch
import pytest
from requests import HTTPError
from shapely.geometry import Point, Polygon

from hydroflows.workflows.events import EventCatalog


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    return Path(__file__).parent / "_data"


@pytest.fixture(scope="session")
def test_data() -> Path:
    """Create a pooch registry for the test data."""
    path = Path(__file__).parent / "_remote_data"
    # get registry from remote to make sure it matches the data
    try:
        base_url = "https://github.com/Deltares-research/HydroFlows/releases/download/test-data"
        _ = pooch.retrieve(
            url=f"{base_url}/registry.txt",
            known_hash=None,
            path=path,
            fname="registry.txt",
        )
    except HTTPError:
        base_url = str(path / "data")
        pass
    # create registry
    test_data = pooch.create(
        # Use the default cache folder for the operating system
        path=path / "data",
        base_url=base_url,
        registry=None,
    )
    test_data.load_registry(path / "registry.txt")
    return test_data


@pytest.fixture(scope="session")
def rio_test_data(test_data) -> str:
    paths = test_data.fetch(
        "rio_data_catalog.zip", processor=pooch.Unzip(extract_dir="rio_data_catalog")
    )
    # return the path to the data catalog file
    path = Path(paths[0]).parent / "data_catalog.yml"
    assert path.is_file()
    return str(path)

@pytest.fixture(scope="session")
def rio_region_path(test_data_dir) -> str:
    return str(test_data_dir / "rio_region.geojson")


@pytest.fixture()
def tmp_csv(tmpdir):
    """Create a temporary csv file."""
    csv_file = tmpdir.join("file.csv")
    csv_file.write("")
    return csv_file




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
