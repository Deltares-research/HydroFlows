# fixtures with input and output files and folders

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from hydroflows.workflows.events import EventCatalog


@pytest.fixture()
def tmp_csv(tmpdir):
    """Create a temporary csv file."""
    csv_file = tmpdir.join("file.csv")
    csv_file.write("")
    return csv_file


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    return Path(__file__).parent / "data"


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
