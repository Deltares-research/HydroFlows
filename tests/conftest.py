import subprocess
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely import Polygon

from hydroflows.methods.events import EventSet


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the path to the testdata directory."""
    return Path(__file__).parent / "_data"


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
def event_set_file(test_data_dir) -> Path:
    """Return the path to the event set yaml."""
    return test_data_dir / "event-sets" / "pluvial_events.yml"


@pytest.fixture()
def event_set(event_set_file) -> EventSet:
    """Return event set."""
    return EventSet.from_yaml(event_set_file)


@pytest.fixture()
def has_snakemake() -> bool:
    """Return True if snakemake is installed."""
    try:
        subprocess.run(["snakemake", "--version"], check=True)
        return True
    except Exception:
        return False
