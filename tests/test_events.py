from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from hydroflows.events import Event, EventSet, Forcing


def test_forcings(tmp_csv: Path, tmp_geojson: Path):
    """Test the Forcing class."""
    forcing = Forcing(
        type="water_level",
        path=str(tmp_csv),
        scale_mult="1",
        scale_add=None,
        locs_path=str(tmp_geojson),
    )
    assert forcing.type == "water_level"
    assert forcing.path == tmp_csv
    assert forcing.locs_path == tmp_geojson
    assert forcing.scale_add is None
    assert forcing.scale_mult == 1.0

    # test with relative path
    forcing = Forcing(
        type="rainfall",
        path=tmp_csv.name,
        _root=tmp_csv.parent.as_posix(),
    )
    assert forcing.path == tmp_csv
    # set root and serialize
    forcing._root = tmp_csv.parent
    data = forcing.model_dump(mode="json")
    assert data["path"] == tmp_csv.name

    with pytest.raises(ValidationError):
        Forcing(type="unknown", path=tmp_csv)


def test_event(tmp_csv: Path, tmp_path: Path):
    """Test the Event class."""
    forcing_dict = {
        "type": "rainfall",
        "path": str(tmp_csv),
        "scale_mult": 1.1,
    }
    event = Event(
        name="event",
        forcings=[forcing_dict],
        return_period=2,
    )
    assert event.name == "event"
    assert event.forcings[0].type == "rainfall"
    assert event.forcings[0].path == tmp_csv
    assert event.forcings[0].scale_mult == 1.1
    assert event.return_period == 2

    # test with relative path
    forcing_dict["path"] = tmp_csv.name
    event = Event(
        name="event",
        forcings=[forcing_dict],
        root=tmp_csv.parent.as_posix(),
    )
    assert event.forcings[0].path == tmp_csv

    # read data
    event.read_forcing_data()
    assert isinstance(event.forcings[0].data, pd.DataFrame)
    assert isinstance(event.tstart, datetime)
    assert all(event.forcings[0].data.values == 1.1)

    # write to yaml
    path_out = tmp_path / "event.yml"
    event.to_yaml(path_out)
    assert path_out.exists()
    event2 = Event.from_yaml(path_out)
    assert event2.to_dict() == event.to_dict()


def test_event_set(test_data_dir: Path):
    event_set = EventSet(
        root=str(test_data_dir / "rainfall_events"),
        events=[
            {"name": "rp050", "path": "event_rp050.yml"},
            {"name": "rp010", "path": "event_rp010.yml"},
        ],
    )
    assert isinstance(event_set.events[0]["path"], Path)
    assert event_set.events[0]["path"].is_absolute()
    assert len(event_set.events) == 2
    event = event_set.get_event("rp050")
    assert isinstance(event, Event)
    assert event.return_period == 50.0


def test_event_set_io(event_set: EventSet, tmp_path: Path):
    # write to yaml
    path_out = tmp_path / "eventset.yml"
    event_set.to_yaml(path_out)
    assert path_out.exists()

    # read from yaml
    event_set2 = EventSet.from_yaml(path_out)
    assert event_set2.root == event_set.root
    assert len(event_set2.events) == len(event_set.events)
