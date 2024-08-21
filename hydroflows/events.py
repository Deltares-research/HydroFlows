"""Defines the Event class which is a breakpoint between workflows."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import geopandas as gpd
import pandas as pd
import xarray as xr
import yaml
from pydantic import (
    BaseModel,
    Field,
    FilePath,
    field_validator,
    model_validator,
)
from typing_extensions import TypedDict

__all__ = ["EventSet"]

SERIALIZATION_KWARGS = {"mode": "json", "round_trip": True, "exclude_none": True}


class Forcing(BaseModel):
    """A forcing for the event."""

    type: Literal["water_level", "discharge", "rainfall"]
    """The type of the forcing."""

    path: Path
    """The path to the forcing data."""

    # Excl from serialization
    data: Optional[Any] = Field(None, exclude=True)
    """The data for the forcing. This is excluded from serialization."""

    time_range: Optional[List[datetime]] = Field(None, exclude=True)
    """The time range of the forcing data. This is excluded from serialization."""

    def read_data(self, root: Optional[Path] = None, **kwargs) -> Any:
        """Read the data."""
        # update and check path
        if root:
            self._set_path_absolute(root)
        self._check_path_exists()
        # read data
        if self.path.suffix == ".csv":
            return self.read_csv(**kwargs)
        else:
            # placeholder for other file types
            raise NotImplementedError(f"File type {self.path.suffix} not supported.")

    def read_csv(self, index_col=0, parse_dates=True, **kwargs) -> pd.DataFrame:
        """Read the CSV file."""
        # read csv; check for datetime index
        # TODO: we could use pandera for more robust data validation
        df: pd.DataFrame = pd.read_csv(
            self.path, index_col=index_col, parse_dates=parse_dates, **kwargs
        )
        if not df.index.dtype == "datetime64[ns]":
            raise ValueError(f"Index of {self.path} is not datetime.")
        self.data = df.sort_index()  # make sure it is sorted
        self.time_range = [df.index[0], df.index[-1]]
        return self.data

    def _set_path_absolute(self, root: Path) -> None:
        """Set the path to be relative to the root."""
        if not self.path.is_absolute() and (root / self.path).exists():
            self.path = root / self.path
        else:
            self.path = self.path.resolve()

    def _set_path_relative(self, root: Path) -> None:
        """Set the path to be relative to the root."""
        if self.path.is_absolute() and self.path.is_relative_to(root):
            self.path = self.path.relative_to(root)

    def _check_path_exists(self) -> None:
        """Check if the path exists."""
        if not self.path.exists():
            raise IOError(f"Forcing {self.path} does not exist.")


class Hazard(BaseModel):
    """A hazard map related to an event."""

    type: Literal["depth", "velocity", "rise_rate"]
    """The type of the forcing."""

    path: Path
    """The path to the hazard data layer (GeoTIFF)."""

    # Excl from serialization
    data: Optional[Any] = Field(None, exclude=True)
    """The data for the hazard. This is excluded from serialization."""

    timestamp: Optional[datetime] = Field(None, exclude=True)
    """Timestamp. This is excluded from serialization."""

    def read_data(self, **kwargs) -> Any:
        """Read the data."""
        # check path
        self._check_path_exists()
        # read data
        if not self.path.suffix == ".tif":
            # placeholder for other file types
            raise NotImplementedError(f"File type {self.path.suffix} not supported.")
        return xr.open_dataset(self.path, **kwargs)

    def _check_path_exists(self) -> None:
        """Check if the path exists."""
        if not self.path.exists():
            raise IOError(f"Hazard data {self.path} does not exist.")

    def _set_path_absolute(self, root: Path) -> None:
        """Set the path to be relative to the root."""
        if not self.path.is_absolute() and (root / self.path).exists():
            self.path = root / self.path
        else:
            self.path = self.path.resolve()

    def _set_path_relative(self, root: Path) -> None:
        """Set the path to be relative to the root."""
        if self.path.is_absolute() and self.path.is_relative_to(root):
            self.path = self.path.relative_to(root)

    def _check_path_exists(self) -> None:
        """Check if the path exists."""
        if not self.path.exists():
            raise IOError(f"Forcing {self.path} does not exist.")


class Impact(BaseModel):
    """An impact map related to an event.

    Impact maps are stored in GeoTIFF raster files or vector files and can be
    embodied by several variables, e.g. damage, affected with several
    arbitrary subcategories such as "content", "building", "infrastructure",
    "population".
    """

    type: Literal["damage", "affected"]  # can be extended
    """The type of the impact."""

    category: Optional[str] = None
    """category of the impact (e.g. "building", "content",
    "population", "infrastructure". To be defined by user."""

    path: Path
    """The path to the hazard data layer (GeoTIFF)."""

    # Excl from serialization
    data: Optional[Any] = Field(None, exclude=True)
    """The data for the hazard. This is excluded from serialization."""

    timestamp: Optional[datetime] = Field(None, exclude=True)
    """Timestamp. This is excluded from serialization."""

    def read_data(self, **kwargs) -> Any:
        """Read the data."""
        # check path
        self._check_path_exists()
        # read data
        if self.path.suffix == ".tif":
            # placeholder for other file types
            return xr.open_dataset(self.path, **kwargs)
        elif self.path.suffix in [".gpkg", "geojson"]:
            # attempt to load as GeoDataSet
            return gpd.read_file(self.path, **kwargs)
        else:
            raise NotImplementedError(f"File type {self.path.suffix} not supported.")

    def _check_path_exists(self) -> None:
        """Check if the path exists."""
        if not self.path.exists():
            raise IOError(f"Impact data {self.path} does not exist.")


class Event(BaseModel):
    """A model event.

    Examples
    --------
    The event can be created as follows::

        from hydroflows.events import Event

        event = Event(
            name="event",
            forcings=[{"type": "rainfall", "path": "path/to/data.csv"}],
            probability=0.5,
        )
    """

    name: str
    """The name of the event."""

    forcings: List[Forcing]
    """The list of forcings for the event. Each forcing is a dictionary with
    the structure as defined in :py:class:`Forcing`."""

    hazards: Optional[List[Hazard]] = None
    """The list of hazard outputs for the event. Each hazard is a dictionary with
    the structure as defined in :py:class:`Hazard`."""

    impacts: Optional[List[Impact]] = None
    """The list of impact outputs for the event. Each impact is a dictionary with
    the structure as defined in :py:class:`Impact`."""

    probability: Optional[float] = None
    """The probability of the event."""

    time_range: Optional[List[datetime]] = None
    """The time range of the event."""

    @field_validator("forcings", mode="before")
    @classmethod
    def _set_forcings(cls, value: Any) -> List[Forcing]:
        # if list of dictionaries, convert to list of Forcing
        if isinstance(value, list) and all(isinstance(f, dict) for f in value):
            return [Forcing(**forcing) for forcing in value]
        return value

    @field_validator("hazards", mode="before")
    @classmethod
    def _set_hazards(cls, value: Any) -> List[Hazard]:
        # if list of dictionaries, convert to list of Forcing
        if isinstance(value, list) and all(isinstance(f, dict) for f in value):
            return [Hazard(**hazard) for hazard in value]
        return value

    @field_validator("impacts", mode="before")
    @classmethod
    def _set_impacts(cls, value: Any) -> List[Impact]:
        # if list of dictionaries, convert to list of Forcing
        if isinstance(value, list) and all(isinstance(f, dict) for f in value):
            return [Impact(**impact) for impact in value]
        return value

    def to_dict(self, **kwargs) -> dict:
        """Return the Event as a dictionary."""
        kwargs = {**SERIALIZATION_KWARGS, **kwargs}
        return self.model_dump(**kwargs)

    def set_time_range_from_forcings(self) -> None:
        """Set the time range from the data."""
        for forcing in self.forcings:
            if forcing.time_range is None:
                continue
            if self.time_range is None:
                self.time_range = forcing.time_range
            else:
                self.time_range[0] = min(self.time_range[0], forcing.time_range[0])
                self.time_range[1] = max(self.time_range[1], forcing.time_range[1])

    def to_yaml(self, path: Path) -> None:
        """Write the Event to a YAML file."""
        # serialize
        yaml_dict = self.to_dict()
        # write to file
        with open(path, "w") as file:
            yaml.safe_dump(yaml_dict, file, sort_keys=False)

    @classmethod
    def from_yaml(cls, path: Path) -> "Event":
        """Create an Event from a YAML file."""
        with open(path, "r") as file:
            yml_dict = yaml.safe_load(file)
        event = cls(**yml_dict)
        # FIXME: this is a bit hacky, but we need to set the path to the parent
        if event.forcings:
            for forcing in event.forcings:
                forcing._set_path_absolute(Path(path).resolve().parent)
        return event

    def read_forcing_data(self) -> None:
        """Read all forcings."""
        for forcing in self.forcings:
            if forcing.data is None:
                forcing.read_data()
        self.set_time_range_from_forcings()


EventDict = TypedDict("EventDict", {"name": str, "path": Path})


class EventSet(BaseModel):
    """A dictionary of events, referring to event file names.

    Examples
    --------
    The event set can be created from a YAML file as follows::

        from hydroflows.events import EventSet

        EventSet.from_yaml("path/to/eventset.yaml")

    The event set can be created from a dictionary as follows::

        from hydroflows.events import EventSet

        EventSet(
            events=[
                {
                    "name": "event1",
                    "path": "path/to/data.csv"
                }
            ],
        )
    """

    root: Optional[Path] = None
    """The root directory for the event files."""

    events: List[EventDict]
    """The list of events. Each event is a dictionary with an event name and reference to an event file. """

    @model_validator(mode="before")
    @classmethod
    def _set_paths(cls, data: Dict) -> Dict:
        """Set the paths to relative to root if not absolute."""
        if "root" in data:
            root = Path(data["root"])
            for event in data["events"]:
                path = event["path"]
                if not Path(path).is_absolute():
                    event["path"] = root / path
        return data

    @classmethod
    def from_yaml(cls, path: Path) -> "EventSet":
        """Create an EventSet from a YAML file."""
        with open(path, "r") as file:
            yaml_dict = yaml.safe_load(file)
        if "root" not in yaml_dict:
            yaml_dict["root"] = Path(path).parent
        return cls(**yaml_dict)

    def to_dict(self, **kwargs) -> dict:
        """Return the EventSet as a dictionary."""
        kwargs = {**SERIALIZATION_KWARGS, **kwargs}
        return self.model_dump(**kwargs)

    def to_yaml(self, path: FilePath) -> None:
        """Write the EventSet to a YAML file."""
        # serialize
        yaml_dict = self.to_dict()
        # make relative paths
        root = path.parent
        for event in yaml_dict["events"]:
            event_path = Path(event["path"])
            """Set the path to be relative to the root."""
            if event_path.is_absolute() and event_path.is_relative_to(root):
                event["path"] = str(event_path.relative_to(root))

        # write to file
        with open(path, "w") as file:
            yaml.safe_dump(yaml_dict, file, sort_keys=False)

    def get_event(self, name: str, raise_error=False) -> Optional[Event]:
        """Get an event by name.

        Parameters
        ----------
        name : str
            The name of the event.
        raise_error : bool, optional
            Raise an error if the event is not found, by default False
            and returns None.
        """
        for event in self.events:
            if event["name"] == name:
                event_file = Path(event["path"])
                return Event.from_yaml(path=event_file)

        if raise_error:
            raise ValueError(f"Event {name} not found.")
        return None

    def get_event_dict(self, name: str, raise_error=False) -> dict:
        """Get an event by name as a dictionary.

        Parameters
        ----------
        name : str
            The name of the event.
        raise_error : bool, optional
            Raise an error if the event is not found, by default False
            and returns an empty dictionary.
        """
        event = self.get_event(name, raise_error=raise_error)
        if event is not None:
            return event.to_dict()
        return {}

    def get_event_data(self, name: str) -> Event:
        """Get an event by name and load its associated data.

        Parameters
        ----------
        name : str
            The name of the event.

        Returns
        -------
        Event
            The event with loaded data.

        Examples
        --------
        The event data can be loaded as follows::

            from hydroflows.events import EventSet

            event_set = EventSet.from_yaml("path/to/events.yaml")
            event = event_set.get_event_data("event1")
            # event data is now loaded
            df = event.forcings[0].data
        """
        # get event
        event = self.get_event(name, raise_error=True)
        # load data
        for forcing in event.forcings:
            if forcing.data is None:
                forcing.read_data(self.roots.root_forcings)
        # set time range
        if event.time_range is None:
            event.set_time_range_from_forcings()
        return event

    def add_event(self, name: str, path: FilePath) -> None:
        """Add an event.

        name : str
            name of the event
        path : FilePath
            Path to yaml file with event description
            See :class:`Event` for the structure of the data in this path.
        """
        event = {"name": name, "path": path}
        self.events.append(event)
