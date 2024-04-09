from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from hydroflows.workflows.events import Event, EventCatalog, Forcing


def test_forcings(tmp_csv):
    """Test the Forcing class."""
    forcings = Forcing(type="rainfall", path=str(tmp_csv))
    assert forcings.type == "rainfall"
    assert forcings.path == tmp_csv

    with pytest.raises(ValidationError):
        Forcing(type="temperature", path=tmp_csv)


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


def test_event_catalog(test_data_dir):
    event_catalog = EventCatalog(
        root=test_data_dir,
        events=[
            {
                "name": "p_rp050",
                "forcings": [{"type": "rainfall", "path": "p_rp050.csv"}],
            },
            {
                "name": "p_rp010",
                "forcings": [{"type": "rainfall", "path": "p_rp010.csv"}],
                "probability": 0.01,
            },
        ],
    )
    assert len(event_catalog.events) == 2
    event = event_catalog.get_event("p_rp050")
    assert isinstance(event, Event)
    assert event.name == "p_rp050"
    assert event_catalog.event_names == ["p_rp050", "p_rp010"]
    assert isinstance(event.forcings, list)
    event_dict = event_catalog.to_dict()
    assert isinstance(event_dict, dict)
    assert isinstance(event_dict["events"], list)
    # set absolute paths
    root = event_catalog.root
    event_catalog.events[0].forcings[0]._set_path_absolute(root)
    assert event.forcings[0].path.is_absolute()
    events_dict = event_catalog.to_dict(relative_paths=True)
    assert not Path(events_dict["events"][0]["forcings"][0]["path"]).is_absolute()
    assert not event.forcings[0].path.is_absolute()


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
