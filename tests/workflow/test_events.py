from pathlib import Path

import pytest
from pydantic import ValidationError

from hydroflows.workflows.events import Driver, Event, EventCatalog


def test_drivers(tmp_csv):
    """Test the EventDrivers class."""
    drivers = Driver(type="rainfall", path=str(tmp_csv))
    assert drivers.type == "rainfall"
    assert drivers.path == tmp_csv

    with pytest.raises(ValidationError):
        Driver(type="temperature", path=tmp_csv)


def test_event(tmp_csv):
    """Test the Event class."""
    event = Event(
        name="event",
        drivers=[{"type": "rainfall", "path": str(tmp_csv)}],
        probability=0.5,
    )
    assert event.name == "event"
    assert event.model_dump()["drivers"][0] == {"type": "rainfall", "path": tmp_csv}
    assert event.probability == 0.5


def test_event_catalog(test_data_dir):
    event_catalog = EventCatalog(
        root=test_data_dir,
        events=[
            {
                "name": "p_rp050",
                "drivers": [{"type": "rainfall", "path": "p_rp050.csv"}],
            },
            {
                "name": "p_rp010",
                "drivers": [{"type": "rainfall", "path": "p_rp010.csv"}],
                "probability": 0.01,
            },
        ],
    )
    assert len(event_catalog.events) == 2
    event = event_catalog.get_event("p_rp050")
    assert isinstance(event, Event)
    assert event.name == "p_rp050"
    assert event_catalog.event_names == ["p_rp050", "p_rp010"]
    assert isinstance(event.drivers, list)
    assert event.drivers[0].path.is_absolute()
    assert event.drivers[0].path.exists()
    event_dict = event_catalog.to_dict()
    assert isinstance(event_dict, dict)
    assert isinstance(event_dict["events"], list)


def test_event_catalog_io(event_catalog, tmpdir):
    # test event catalog round trip
    event_yml = Path(tmpdir) / "events.yaml"
    event_catalog.to_yaml(event_yml)
    assert event_yml.exists()
    event_catalog2 = EventCatalog.from_yaml(event_yml)
    assert event_catalog == event_catalog2
