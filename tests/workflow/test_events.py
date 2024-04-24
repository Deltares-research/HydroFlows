from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from hydroflows.workflows.events import Event, EventCatalog, Forcing, Hazard, Impact


def test_forcings(tmp_csv):
    """Test the Forcing class."""
    forcings = Forcing(type="rainfall", path=str(tmp_csv))
    assert forcings.type == "rainfall"
    assert forcings.path == tmp_csv

    with pytest.raises(ValidationError):
        Forcing(type="temperature", path=tmp_csv)


def test_hazard(tmp_tif):
    """Test the Forcing class."""
    hazard = Hazard(type="depth", path=str(tmp_tif))
    assert hazard.type == "depth"
    assert hazard.path == tmp_tif

    with pytest.raises(ValidationError):
        Forcing(type="unsupported_variable", path=tmp_tif)


@pytest.mark.parametrize(
    "file", ["tmp_tif", "tmp_geojson"]
)
def test_impact(file, request):
    file = request.getfixturevalue(file)
    """Test the Forcing class."""
    impact = Impact(type="affected", path=str(file))
    assert impact.type == "affected"
    assert impact.path == file

    with pytest.raises(ValidationError):
        Forcing(type="unsupported_variable", path=file)



def test_event(tmp_csv):
    """Test the Event class."""
    event = Event(
        name="event",
        forcings=[{"type": "rainfall", "path": str(tmp_csv)}],
        probability=0.5,
    )
    assert event.name == "event"
    assert event.model_dump()["forcings"][0] == {"type": "rainfall", "path": tmp_csv}
    assert event.probability == 0.5


def test_forcing_event_catalog(test_data_dir):
    event_catalog = EventCatalog(
        roots={"root_forcings": test_data_dir},
        events=[
            {
                "name": "rp050",
                "forcings": [{"type": "rainfall", "path": "rainfall_rp050.csv"}],
            },
            {
                "name": "rp010",
                "forcings": [{"type": "rainfall", "path": "rainfall_rp010.csv"}],
                "probability": 0.01,
            },
        ],
    )
    assert len(event_catalog.events) == 2
    event = event_catalog.get_event("rp050")
    assert isinstance(event, Event)
    assert event.name == "rp050"
    assert event_catalog.event_names == ["rp050", "rp010"]
    assert isinstance(event.forcings, list)
    event_dict = event_catalog.to_dict()
    assert isinstance(event_dict, dict)
    assert isinstance(event_dict["events"], list)
    # set absolute paths
    root_forcing = event_catalog.roots.root_forcings
    event_catalog.events[0].forcings[0]._set_path_absolute(root_forcing)
    assert event.forcings[0].path.is_absolute()
    events_dict = event_catalog.to_dict(relative_paths=True)
    assert not Path(events_dict["events"][0]["forcings"][0]["path"]).is_absolute()
    assert not event.forcings[0].path.is_absolute()


def test_hazard_impact_event_catalog(test_data_dir):
    event_catalog = EventCatalog(
        roots={"root_forcings": test_data_dir},
        events=[
            {
                "name": "rp050",
                "forcings": [{"type": "rainfall", "path": "rainfall_rp050.csv"}],
                "hazards": [
                    {"type": "depth", "path": "flood_depth_rp050.tif"},
                    {"type": "velocity", "path": "velocity_rp050.tif"},
                ],
                "impacts": [
                    {"type": "damage", "category": "all", "path":
                        "damage_schools_rp050.tif"},  # example for grid output
                    {"type": "damage", "category": "schools", "path":
                        "damage_schools_rp050.gpkg"},  # example for vector output
                ]
            },
            {
                "name": "p_rp010",
                "forcings": [{"type": "rainfall", "path": "p_rp010.csv"}],
                "hazards": [
                    {"type": "depth", "path": "depth_p_rp010.tif"},
                    {"type": "velocity", "path": "velocity_p_rp010.tif"},
                ],
                "impacts": [
                    {"type": "damage", "category": "all", "path":
                        "damage_schools_p_rp010.tif"},  # example for grid output
                    {"type": "damage", "category": "schools", "path":
                        "damage_schools_p_rp010.gpkg"},  # example for vector output
                ],
                "probability": 0.01,
            },
        ],
    )
    event = event_catalog.get_event("p_rp050")
    assert isinstance(event.hazards, list)
    assert isinstance(event.impacts, list)
    event_dict = event_catalog.to_dict()
    assert isinstance(event_dict, dict)
    assert isinstance(event_dict["events"], list)
    # set absolute paths
    event_catalog.to_dict(relative_paths=True)
    event_catalog.to_yaml("catalog.yml")


def test_event_catalog_io(event_catalog, tmpdir):
    # test event catalog round trip
    event_yml = Path(tmpdir) / "events.yaml"
    event_catalog.to_yaml(event_yml)
    assert event_yml.exists()
    event_catalog2 = EventCatalog.from_yaml(event_yml)
    assert event_catalog == event_catalog2


def test_event_catalog_data(event_catalog):
    # test event catalog data
    event = event_catalog.get_event_data("p_rp050")
    assert all(isinstance(d.data, pd.DataFrame) for d in event.forcings)
    assert event.time_range is not None
