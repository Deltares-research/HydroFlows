"""Defines the Event class which is a breakpoint between workflows."""

from datetime import datetime
from pathlib import Path
from typing import Any, List, Literal, Optional, Union

import geopandas as gpd
import pandas as pd
import xarray as xr
import yaml
from pydantic import (
    BaseModel,
    DirectoryPath,
    Field,
    FilePath,
    field_validator,
)

__all__ = ["EventCatalog"]

SERIALIZATION_KWARGS = {"mode": "json", "round_trip": True, "exclude_none": True}


class Forcing(BaseModel):
    """A forcing for the event.

    Parameters
    ----------
    type : Literal["water_level", "discharge", "rainfall"]
        The type of the forcing.
    path : Path
        The path to the forcing data.
    data : Any, optional
        The data for the forcing, by default None.
        This is excluded from serialization.
    time_range : datetime, optional
        The time range of the forcing data, by default None.
        This is excluded from serialization.
    """

    type: Literal["water_level", "discharge", "rainfall"]
    path: Path
    # Excl from serialization
    data: Optional[Any] = Field(None, exclude=True)
    time_range: Optional[List[datetime]] = Field(None, exclude=True)

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
        df = pd.read_csv(
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
    """A hazard map related to an event.

    Hazard maps are stored in GeoTIFF raster files and can be embodied by several
    variables, e.g. depth, velocity, rise rate.

    Parameters
    ----------
    type : Literal["depth", "velocity", "rise_rate"]
        The type of the forcing.
    path : Path
        The path to the hazard data layer (GeoTIFF).
    data : Any, optional
        The data for the hazard, by default None.
        This is excluded from serialization.

    """

    type: Literal["depth", "velocity", "rise_rate"]
    path: Path
    # Excl from serialization
    data: Optional[Any] = Field(None, exclude=True)
    timestamp: Optional[datetime] = Field(None, exclude=True)

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


class Impact(BaseModel):
    """An impact map related to an event.

    Impact maps are stored in GeoTIFF raster files or vector files and can be
    embodied by several variables, e.g. damage, affected with several
    arbitrary subcategories such as "content", "building", "infrastructure",
    "population"

    Parameters
    ----------
    type : Literal["damage", "affected"]
        The type of the impact.
    category : Optional[str] : category of the impact (e.g. "building", "content",
        "population", "infrstructure". To be defined by user.
    path : Path
        The path to the hazard data layer (GeoTIFF).
    data : Any, optional
        The data for the hazard, by default None.
        This is excluded from serialization.

    """

    type: Literal["damage", "affected"]  # can be extended
    category: Optional[str] = None
    path: Path
    # Excl from serialization
    data: Optional[Any] = Field(None, exclude=True)
    timestamp: Optional[datetime] = Field(None, exclude=True)

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

    Parameters
    ----------
    name : str
        The name of the event.
    forcings : List[Forcing]
        The list of forcings for the event. Each forcing is a dictionary with
        the structure as defined in :class:`Forcing`.
    hazards : Optional[List[Hazard]]
        The list of hazard outputs for the event. Each hazard is a dictionary with
        the structure as defined in :class:`Hazard`.
    impacts : Optional[List[Impact]]
        The list of impact outputs for the event. Each impact is a dictionary with
        the structure as defined in :class:`Impact`.
    probability : float, optional
        The probability of the event, by default None.
    time_range : List[datetime], optional
        The time range of the event, by default None.

    Examples
    --------
    The event can be created as follows:

        ```python
        from hydroflows.workflows.events import Event
        event = Event(
            name="event",
            forcings=[dict(type="rainfall", path="path/to/data.csv")],
            probability=0.5,
        )
        ````
    """

    name: str
    forcings: List[Forcing]
    hazards: Optional[List[Hazard]] = None
    impacts: Optional[List[Impact]] = None
    probability: Optional[float] = None
    time_range: Optional[List[datetime]] = None


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
                self.time_range[0] = min(
                    self.time_range[0], forcing.time_range.index[0]
                )
                self.time_range[1] = max(
                    self.time_range[1], forcing.time_range.index[1]
                )


class Roots(BaseModel):
    """Dictionary of directories for event files.

    Parameters
    ----------
    root_forcings : Optional[DirectoryPath]
        Root directory for forcing data.
    root_hazards : Optional[DirectoryPath]
        Root directory for hazard data.
    root_impacts : Optional[DirectoryPath]
        Root directory for impact data.

    """

    root_forcings: Optional[DirectoryPath] = None
    root_hazards: Optional[DirectoryPath] = None
    root_impacts: Optional[DirectoryPath] = None


class EventCatalog(BaseModel):
    """A dictionary of event configurations.

    Parameters
    ----------
    version : str
        The version of the event catalog.
    roots : Roots
        The root directories for forcings, hazards and impacts for the event catalog.
    events : List[Event]
        The list of events. Each event is a dictionary with the structure
        as defined in :class:`Event`.

    Examples
    --------
    The event catalog can be created from a YAML file as follows:

        ```python
        from hydroflows.workflows.events import EventCatalog
        EventCatalog.from_yaml("path/to/events.yaml")
        ````

    The event catalog can be created from a dictionary as follows:

        ```python
        from hydroflows.workflows.events import EventCatalog
        EventCatalog(
            root="path/to/root",
            events=[
                {
                    "name": "event1",
                    "forcings": [{"type": "rainfall", "path": "path/to/data.csv"}],
                    "probability": 0.5, # optional
                }
            ],
        )
        ````
    """

    version: str = "v0.1"
    roots: Optional[Roots] = Roots()
    # root: Optional[DirectoryPath] = None
    events: List[Event]

    @field_validator("events", mode="before")
    @classmethod
    def _set_events(cls, value: Any) -> List[Event]:
        # if list of dictionaries, convert to list of Event
        if isinstance(value, list) and all(isinstance(f, dict) for f in value):
            return [Event(**event) for event in value]
        return value

    @property
    def event_names(self) -> list[str]:
        """Return a list of event names."""
        return [event.name for event in self.events]

    @classmethod
    def from_yaml(cls, path: FilePath) -> "EventCatalog":
        """Create an EventCatalog from a YAML file."""
        with open(path, "r") as file:
            yml_dict = yaml.safe_load(file)
        if "roots" not in yml_dict:  # set root to parent of path
            yml_dict["roots"] = Roots(**{
                "root_forcings": Path(path).parent,
                "root_hazards": Path(path).parent,
                "root_impacts": Path(path).parent,
            })
        else:
            yml_dict["roots"] = Roots(**yml_dict["roots"])
        return cls(**yml_dict)

    def set_forcing_paths_relative_to_root(self) -> None:
        """Set all forcing paths relative to root."""
        if self.roots is None:
            return
        if self.roots.root_forcings is not None:
            for event in self.events:
                for forcing in event.forcings:
                    forcing._set_path_relative(self.roots.root_forcings)

    def to_dict(self, relative_paths=False, **kwargs) -> dict:
        """Return the EventCatalog as a dictionary."""
        # set all forcing paths relative to root
        if relative_paths:
            self.set_forcing_paths_relative_to_root()
        kwargs = {**SERIALIZATION_KWARGS, **kwargs}
        return self.model_dump(**kwargs)

    def to_yaml(self, path: FilePath) -> None:
        """Write the EventCatalog to a YAML file."""
        # serialize
        yaml_dict = self.to_dict(relative_paths=True)
        # remove root if parent of path
        if "roots" in yaml_dict:
            for k in ["root_forcings", "root_hazards", "root_impacts"]:
                # remove all paths
                if k in yaml_dict["roots"]:
                    if Path(yaml_dict["roots"][k]) == Path(path).parent:
                        del yaml_dict["roots"][k]
            # if roots is an empty dict, then remove alltogether
            if not yaml_dict["roots"]:
                del yaml_dict["roots"]

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
            if event.name == name:
                return event
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
        The event data can be loaded as follows:

            ```python
            from hydroflows.workflows.events import EventCatalog
            event_catalog = EventCatalog.from_yaml("path/to/events.yaml")
            event = event_catalog.get_event_data("event1")
            # event data is now loaded
            df = event.forcings[0].data
            ````
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

    def add_event(self, event: Union[Event, dict]) -> None:
        """Add an event.

        event : Union[Event, dict]
            The event to add.
            See :class:`Event` for the event structure.
        """
        if isinstance(event, dict):
            event = Event(**event)
        self.events.append(event)
