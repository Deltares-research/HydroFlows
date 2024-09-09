"""Defines the Event class which is a breakpoint between workflows."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import geopandas as gpd
import pandas as pd
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)
from typing_extensions import TypedDict

__all__ = ["EventSet"]

SERIALIZATION_KWARGS = {"mode": "json", "round_trip": True, "exclude_none": True}


class Forcing(BaseModel):
    """A forcing for the event."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["water_level", "discharge", "rainfall"]
    """The type of the forcing."""

    path: Path
    """The path to the forcing data."""

    tstart: Optional[datetime] = None
    """The start date of the forcing data"""

    tstop: Optional[datetime] = None
    """The end date of the forcing data"""

    scale_mult: Optional[float] = None
    """A multiplicative scale factor for the forcing."""

    scale_add: Optional[float] = None
    """An additive scale factor for the forcing."""

    locs_path: Optional[Path] = None
    """The path to the locations file for the forcing data."""

    locs_id_col: Optional[str] = None
    """The column in the locations file with the location ID."""

    # Excl from serialization
    _data_df: Optional[pd.DataFrame] = None
    """The forcing data. This is excluded from serialization."""

    _locs_gdf: Optional[gpd.GeoDataFrame] = None
    """Optional field with geolocation of data. This field is excluded from serialization."""

    _root: Optional[Path] = None
    """The root directory for the forcing and location data."""

    @model_validator(mode="before")
    @classmethod
    def _set_abs_paths(cls, data: Dict) -> Dict:
        """Set the paths to relative to root if not absolute."""
        if isinstance(data, dict) and "_root" in data:
            root = Path(data.pop("_root"))
            data = _rel_to_abs_path(data, ["path", "locs_path"], root)
        return data

    @model_serializer(mode="wrap", when_used="json")
    def _set_rel_paths(self, nxt: SerializerFunctionWrapHandler):
        """Serialize paths as relative to root."""
        data = nxt(self)
        if self._root:
            data = _abs_to_rel_path(
                data, ["path", "locs_path"], Path(self._root), serialize=True
            )
        return data

    def read_data(self) -> Any:
        """Read the data."""
        # update and check path
        if not self.path.exists():
            raise IOError(f"Forcing {self.path} does not exist.")

        # read forcing data
        if self.path.suffix == ".csv":
            self._read_csv()
        else:
            # placeholder for other file types
            raise NotImplementedError(f"File type {self.path.suffix} not supported.")

        # read locations
        if self.locs_path is None:
            return
        if not self.locs_path.exists():
            raise IOError(f"Locations file {self.locs_path} does not exist.")
        # should be readable by geopandas
        self._read_locs_geopandas()

    def _read_locs_geopandas(self) -> None:
        """Read the locations file using geopandas."""
        gdf = gpd.read_file(self.locs_path)
        if self.locs_id_col is not None:
            gdf = gdf.set_index(self.locs_id_col)
        self._locs_gdf = gdf

    def _read_csv(self) -> None:
        """Read the CSV file."""
        # read csv; check for datetime index
        df: pd.DataFrame = pd.read_csv(self.path, index_col=0, parse_dates=True)
        if not df.index.dtype == "datetime64[ns]":
            raise ValueError(f"Index of {self.path} is not datetime.")
        df = df.sort_index()  # make sure it is sorted
        # apply scale factor
        if self.scale_mult is not None:
            df = df * self.scale_mult
        if self.scale_add is not None:
            df = df + self.scale_add
        # clip data to tstart, tstop
        if self.tstart is None:
            self.tstart = df.index[0]
        if self.tstop is None:
            self.tstop = df.index[-1]
        if self.tstart > df.index[-1] or self.tstop < df.index[0]:
            df = df.loc[slice(self.tstart, self.tstop)]
        # set data
        self._data_df = df

    @property
    def data(self) -> pd.DataFrame:
        """Return the forcing data."""
        if self._data_df is None:
            self.read_data()
        return self._data_df

    @property
    def locs(self) -> Optional[gpd.GeoDataFrame]:
        """Return the locations data."""
        if self._locs_gdf is None and self.locs_path is not None:
            self.read_data()
        return self._locs_gdf


class Event(BaseModel):
    """A model event.

    Examples
    --------
    The event can be created as follows::

        event = Event(
            name="event",
            forcings=[{"type": "rainfall", "path": "path/to/data.csv"}],
            probability=0.5,
        )
    """

    name: str
    """The name of the event."""

    root: Optional[Path] = None
    """The root directory for the event forcing."""

    forcings: List[Forcing]
    """The list of forcings for the event. Each forcing is a dictionary with
    the structure as defined in :py:class:`Forcing`."""

    return_period: Optional[float] = None
    """The return period of the event [years]."""

    tstart: Optional[datetime] = None
    """The start date of the event."""

    tstop: Optional[datetime] = None
    """The end date of the event."""

    @model_validator(mode="before")
    @classmethod
    def _forward_root(cls, data: Dict) -> Dict:
        """Forward root to forcings."""
        if "root" in data:
            for forcing in data["forcings"]:
                forcing["_root"] = data["root"]
        return data

    def to_dict(self, root: Optional[Path] = None, **kwargs) -> dict:
        """Return the Event as a dictionary."""
        # set forings root to path.parent
        root = root or self.root
        if root is not None:
            for forcing in self.forcings:
                forcing._root = Path(root)
        # serialize
        kwargs = {**SERIALIZATION_KWARGS, **kwargs}
        data = self.model_dump(**kwargs)
        # reset forcings root
        for forcing in self.forcings:
            forcing._root = None
        return data

    def to_yaml(self, path: Path) -> None:
        """Write the Event to a YAML file."""
        path = Path(path)
        root = self.root
        # check if all forcing.path relative to path.parent, if so use path.parent as root
        if root is None and all(
            forcing.path.is_relative_to(path.parent) for forcing in self.forcings
        ):
            root = path.parent
        # serialize
        yaml_dict = self.to_dict(root=root)
        # remove root if it is the same as path.parent
        if "root" in yaml_dict and Path(yaml_dict["root"]) == path.parent:
            yaml_dict.pop("root")
        # write to file
        with open(path, "w") as file:
            yaml.safe_dump(yaml_dict, file, sort_keys=False)

    @classmethod
    def from_yaml(cls, path: Path) -> "Event":
        """Create an Event from a YAML file."""
        with open(path, "r") as file:
            yml_dict = yaml.safe_load(file)
        # set root
        if "root" not in yml_dict:
            yml_dict["root"] = Path(path).parent
        return cls(**yml_dict)

    def set_time_range_from_forcings(self) -> None:
        """Set the time range from the data."""
        for forcing in self.forcings:
            if forcing.tstart is None or forcing.tstop is None:
                continue
            if self.tstart is None or self.tstop is None:
                self.tstart = forcing.tstart
                self.tstop = forcing.tstop
            else:
                self.tstart = min(self.tstart, forcing.tstart)
                self.tstop = max(self.tstop, forcing.tstop)

    def read_forcing_data(self) -> None:
        """Read all forcings."""
        for forcing in self.forcings:
            if forcing.data is None:
                forcing.read_data()
        if self.tstart is None or self.tstop is None:
            self.set_time_range_from_forcings()


EventDict = TypedDict("EventDict", {"name": str, "path": Path})


class EventSet(BaseModel):
    """A dictionary of events, referring to event file names.

    Examples
    --------
    The event set can be created from a YAML file as follows::

        EventSet.from_yaml("path/to/eventset.yaml")

    The event set can be created from a dictionary as follows::

        EventSet(
            events=[
                {
                    "name": "event1",
                    "path": "path/to/event1.yml"
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
    def _set_abs_paths(cls, data: Dict) -> Dict:
        """Set the paths to relative to root if not absolute."""
        if "root" in data:
            root = Path(data["root"])
            events = []
            for event in data["events"]:
                events.append(_rel_to_abs_path(event, ["path"], root))
            data["events"] = events
        return data

    @model_serializer(mode="wrap", when_used="json")
    def _set_rel_paths(self, nxt: SerializerFunctionWrapHandler):
        """Serialize paths as relative to root."""
        data = nxt(self)
        if self.root:
            events = []
            for event in data["events"]:
                events.append(
                    _abs_to_rel_path(event, ["path"], self.root, serialize=True)
                )
            data["events"] = events
            data["root"] = self.root.as_posix()
        return data

    @classmethod
    def from_yaml(cls, path: Path) -> "EventSet":
        """Create an EventSet from a YAML file."""
        with open(path, "r") as file:
            yaml_dict = yaml.safe_load(file)
        if "root" not in yaml_dict:
            yaml_dict["root"] = Path(path).parent
        return cls(**yaml_dict)

    def to_dict(self, root: Optional[Path] = None, **kwargs) -> dict:
        """Return the EventSet as a dictionary."""
        # new root
        if root:
            root = Path(root)
            old_root = self.root
            self.root = root
        kwargs = {**SERIALIZATION_KWARGS, **kwargs}
        data = self.model_dump(**kwargs)
        # reset root
        if root:
            self.root = old_root
        return data

    def to_yaml(self, path: Path) -> None:
        """Write the EventSet to a YAML file."""
        root = self.root
        # check if all events relative to path.parent, if so reset root
        if all(event["path"].is_relative_to(path.parent) for event in self.events):
            root = path.parent

        # serialize
        yaml_dict = self.to_dict(root=root)

        # remove root if it is the same as path.parent
        if "root" in yaml_dict and Path(yaml_dict["root"]) == path.parent:
            yaml_dict.pop("root")

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
                return Event.from_yaml(path=event["path"])

        if raise_error:
            raise ValueError(f"Event {name} not found.")
        return None

    def add_event(self, name: str, path: Path) -> None:
        """Add an event.

        name : str
            name of the event
        path : Path
            Path to yaml file with event description
            See :class:`Event` for the structure of the data in this path.
        """
        event = {"name": name, "path": path}
        self.events.append(event)


def _rel_to_abs_path(data: Dict, keys: List[str], root: Path) -> Dict:
    for key in keys:
        if key in data and not Path(data[key]).is_absolute():
            data[key] = root / Path(data[key])
    return data


def _abs_to_rel_path(data: Dict, keys: List[str], root: Path, serialize=True) -> Dict:
    for key in keys:
        if key not in data or data[key] is None:
            continue
        path = Path(data[key])
        if path.is_relative_to(root):
            path = path.relative_to(root)
        if serialize:
            data[key] = path.as_posix()
    return data
