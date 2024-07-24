import pytest
from pydantic import ValidationError

from hydroflows.events import Event, EventSet, Forcing, Hazard, Impact


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


@pytest.mark.parametrize("file", ["tmp_tif", "tmp_geojson"])
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


def test_event_set(test_data_dir):
    event_set = EventSet(
        root=test_data_dir,
        events=[
            {"name": "rp050", "path": "event_rp050.yml"},
            {"name": "rp010", "path": "event_rp010.yml"},
        ],
    )
    assert len(event_set.events) == 2
    event = event_set.get_event("rp050")
    assert isinstance(event, Event)


def test_event_set_io(event_set):
    event = event_set.get_event("rp050")
    assert isinstance(event, Event)
