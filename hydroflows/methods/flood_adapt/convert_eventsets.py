import shutil  # noqa: D100
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd
import tomli
import tomli_w
from flood_adapt import unit_system as us
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.event_set import EventSet, EventSetModel
from flood_adapt.object_model.hazard.event.template_event import EventModel
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
)
from flood_adapt.object_model.hazard.forcing.rainfall import RainfallCSV
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelModel,
)
from flood_adapt.object_model.hazard.forcing.wind import WindConstant
from flood_adapt.object_model.interface.config.sfincs import RiverModel
from pydantic import BaseModel


class Source(str, Enum):
    """An enumeration representing different types of data sources.

    Attributes
    ----------
    TIMESERIES: Represents a time series data source.
    CONSTANT: Represents a constant value data source.
    NONE: Represents the absence of a data source.
    MODEL: Represents a model-based data source.
    TRACK: Represents a track-based data source.
    """

    TIMESERIES = "timeseries"
    CONSTANT = "constant"
    NONE = "none"
    MODEL = "model"
    TRACK = "track"


class TimeModel(BaseModel):
    """
    Represents a time model with start and end times.

    Attributes
    ----------
    start_time (str): The starting time of the event or period.
    end_time (str): The ending time of the event or period.
    """

    start_time: str
    end_time: str


class RiverModels(BaseModel):
    """
    A model representing a river system configuration.

    Attributes
    ----------
    source : Source
    The data source type for the river model.
    constant_discharge : Optional[us.UnitfulDischarge]
    The constant discharge value, if applicable.
    timeseries_file : Optional[str]
    The path to the timeseries file, if applicable.
    """

    source: Source
    constant_discharge: Optional[us.UnitfulDischarge] = None
    timeseries_file: Optional[str] = None


class WindModel(BaseModel):
    """
    A model representing wind data with optional attributes for speed and direction.

    Attributes
    ----------
    source : Source
    The data source for the wind model, defined by the Source enumeration.
    wind_speed : Optional[us.UnitfulVelocity]
    The wind speed, represented as an optional unitful velocity.
    wind_direction : Optional[us.UnitfulDirection]
    The wind direction, represented as an optional unitful direction.
    """

    source: Source
    wind_speed: Optional[us.UnitfulVelocity] = None
    wind_direction: Optional[us.UnitfulDirection] = None


class RainfallModel(BaseModel):
    """
    A model representing rainfall data for flood adaptation.

    Attributes
    ----------
    source : Source
    The source of the rainfall data, defined by the Source enumeration.
    rainfall_intensity : Optional[us.UnitfulIntensity]
    The intensity of the rainfall, with units, if applicable.
    timeseries_file : Optional[str]
    The file path to the timeseries data, if available.
    """

    source: Source
    rainfall_intensity: Optional[us.UnitfulIntensity] = None
    timeseries_file: Optional[str] = None


class TideModel(BaseModel):
    """
    A model representing tide data configuration.

    Attributes
    ----------
    source : Source
    The data source for the tide model, specified as a member of the Source enumeration.
    timeseries_file : Optional[str]
    The path to the file containing time series data for the tide model, if applicable.
    """

    source: Source
    timeseries_file: Optional[str] = None


class SurgeModel(BaseModel):
    """
    A data model representing a surge event configuration.

    Attributes
    ----------
    source : Source
    The data source for the surge model, defined by the Source enumeration.
    shape_type : Optional[str]
    The type of shape used in the model, if applicable.
    timeseries_file : Optional[str]
    The path to the file containing time series data for the model, if applicable.
    """

    source: Source
    shape_type: Optional[str] = None
    timeseries_file: Optional[str] = None


class OldEvent(BaseModel):
    """
    A model representing an old event configuration with various environmental factors.

    Attributes
    ----------
    name : str
        The name of the event.
    description : str
        A brief description of the event.
    template : str
        The template associated with the event.
    water_level_offset : us.UnitfulLength
        The offset for water level measurements.
    timing : str
        The timing details of the event.
    time : TimeModel
        The time model associated with the event.
    mode : str
        The mode of the event.
    river : Optional[list[RiverModels]]
        A list of river models associated with the event, if any.
    wind : Optional[WindModel]
        The wind model associated with the event, if any.
    rainfall : Optional[RainfallModel]
        The rainfall model associated with the event, if any.
    tide : Optional[TideModel]
        The tide model associated with the event, if any.
    surge : Optional[SurgeModel]
        The surge model associated with the event, if any.
    track_name : Optional[str]
        The name of the track associated with the event, if any.
    """

    name: str
    description: str = ""
    template: str
    water_level_offset: us.UnitfulLength
    timing: str = ""
    time: TimeModel
    mode: str

    river: Optional[list[RiverModels]] = None
    wind: Optional[WindModel] = None
    rainfall: Optional[RainfallModel] = None
    tide: Optional[TideModel] = None
    surge: Optional[SurgeModel] = None
    track_name: Optional[str] = None


def convert_event(
    old_event: dict,
    old_event_dir: Path,
) -> EventModel:
    """
    Convert an old event configuration dictionary into a new EventModel instance.

    This function takes a dictionary representing an old event configuration and
    converts it into a new EventModel instance using the organization's object model.
    It processes various environmental factors such as wind, rainfall, river discharge,
    and tide, and maps them to the appropriate forcing models. The function raises
    a ValueError if unexpected sources are encountered or if no tide or surge is found.

    Parameters
    ----------
    old_event : dict
        A dictionary containing the old event configuration.
    old_event_dir : Path
        The directory path where event-related files are stored.

    Returns
    -------
    EventModel
        The converted EventModel instance.
    """
    to_convert = OldEvent(**old_event).model_dump()
    attrs = {
        "name": to_convert["name"],
        "description": to_convert["description"],
        "mode": to_convert["mode"],
        "template": to_convert["template"],
        "time": to_convert["time"],
    }
    forcings = {}
    if wind := to_convert.get("wind"):
        if wind["source"] == Source.CONSTANT:
            _wind = WindConstant(
                speed=wind["wind_speed"],
                direction=wind["wind_direction"],
            )
            forcings.update({"WIND": [_wind]})
        elif wind["source"] == Source.NONE:
            pass
        #### In the wind class add all the forcing - can be a time series??
        else:
            raise ValueError(f"other wind found: {wind}")

    if rainfall := to_convert.get("rainfall"):
        if rainfall["source"] == Source.TIMESERIES:
            _rainfall = RainfallCSV(path=old_event_dir / rainfall["timeseries_file"])
            forcings.update({"RAINFALL": [_rainfall]})
        elif rainfall["source"] == Source.NONE:
            pass
        else:
            raise ValueError(f"other wind found: {rainfall}")

    if river := to_convert.get("river"):
        if river[0]["constant_discharge"] is not None:
            _river = [
                DischargeConstant(
                    river=RiverModel(
                        name="Cooper River",  # TODO dummy name. This information should be saved by hydroflows
                        mean_discharge=us.UnitfulDischarge(value=5000, units="cfs"),
                        x_coordinate=595546.3,  # TODO dummy coordinates. This information should be saved by hydroflows
                        y_coordinate=3675590.6,  # TODO dummy coordinates. This information should be saved by hydroflows
                    ),
                    discharge=river[0]["constant_discharge"],
                )
            ]
        else:
            if len(river) == 1:
                discharge_csv = pd.read_csv(old_event_dir / river[0]["timeseries_file"])
                mean_discharge = int(discharge_csv.iloc[0:, 1].mean())
                _river = [
                    DischargeCSV(
                        river=RiverModel(
                            name="Cooper River",  # TODO dummy name
                            mean_discharge=us.UnitfulDischarge(
                                value=mean_discharge, units="m3/s"
                            ),
                            x_coordinate=595546.3,  # TODO dummy coordinates. This information should be saved by hydroflows
                            y_coordinate=3675590.6,  # TODO dummy coordinates. This information should be saved by hydroflows
                        ),
                        path=old_event_dir / river[0]["timeseries_file"],
                        units="m3/s",  # TODO check if this is always the unit
                    )
                ]
            else:
                _river = []
                for i in river:
                    discharge_csv = pd.read_csv(old_event_dir / i["timeseries_file"])
                    mean_discharge = int(discharge_csv.iloc[0:, 0].mean())
                    _i = DischargeCSV(
                        river=RiverModel(
                            name="Cooper River",  # TODO dummy name
                            mean_discharge=us.UnitfulDischarge(
                                value=mean_discharge, units="m3/s"
                            ),
                            x_coordinate=595546.3,  # TODO dummy coordinates. This information should be saved by hydroflows
                            y_coordinate=3675590.6,  # TODO dummy coordinates. This information should be saved by hydroflows
                        ),
                        path=old_event_dir / i["timeseries_file"],
                        units="m3/s",  # TODO check if this is always the unit
                    )
                    _river.append(_i)

        forcings.update({"DISCHARGE": _river})

    if tide := to_convert.get("tide"):
        if tide["source"] == Source.TIMESERIES:
            _waterlevel = WaterlevelCSV(path=old_event_dir / tide["timeseries_file"])
            forcings.update({"WATERLEVEL": [_waterlevel]})
        elif tide["source"] == Source.MODEL:
            _waterlevel = WaterlevelModel()
            forcings.update({"WATERLEVEL": [_waterlevel]})
        else:
            raise ValueError("other source tide or surge found")
    else:
        raise ValueError("No tide or surge found")

    attrs["forcings"] = forcings

    if to_convert.get("template") == "Hurricane":
        attrs["track_name"] = to_convert["name"]

    new_event = EventFactory.load_dict(attrs)

    return new_event


def convert_eventset(old_path: Path, new_path: Path):
    """
    Convert an old event set to a new format and save it to a specified path.

    This function reads sub-events and frequency data from an old event set located at
    the given old_path, converts them into a new EventSet format, and saves the new
    event set to the specified new_path.

    Parameters
    ----------
    old_path : Path
        The directory path containing the old event set configuration files.
    new_path : Path
        The directory path where the new event set will be saved.

    Returns
    -------
    EventSet
        The newly created EventSet instance.
    """
    new_set = EventSet(
        data=EventSetModel(
            name="Probabilistic_set",
            description="Probabilistic set",
            sub_events=read_sub_events(old_path),
            frequency=read_frequencies(old_path),
        )
    )
    new_path.mkdir(exist_ok=True, parents=True)
    new_set.save(new_path / f"{new_path.name}.toml")
    return new_set


def read_sub_events(path: Path) -> list[EventModel]:
    """
    Read and convert sub-events from a specified directory path into a list of EventModel instances.

    This function reads a set of sub-event configurations from a directory, converts each
    sub-event using the organization's object model, and returns a list of the converted
    EventModel instances. Each sub-event is expected to be stored in a TOML file within
    the specified path.

    Parameters
    ----------
    path : Path
        The directory path containing sub-event configuration files.

    Returns
    -------
    list[EventModel]
        A list of converted EventModel instances.
    """
    old_event_set_file = path / f"{path.name}.toml"
    with open(old_event_set_file, "rb") as f:
        old_event_set = tomli.load(f)

    sub_events = []
    for sub_event in old_event_set["subevent_name"]:
        sub_event_path = path / sub_event / f"{sub_event}.toml"

        old_event = read_old_event(sub_event_path)
        new_event = convert_event(old_event, sub_event_path.parent)

        sub_events.append(new_event.attrs.model_dump())
    return sub_events


def read_frequencies(path: Path) -> list[float]:
    """
    Read frequency values from a TOML file associated with the given path.

    Parameters
    ----------
    path : Path
        The directory path to th TOML files.

    Returns
    -------
        list[float]: A list of frequency values extracted from the TOML file.
    """
    old_event_set_file = path / f"{path.name}.toml"
    with open(old_event_set_file, "rb") as f:
        old_event_set = tomli.load(f)
    return old_event_set["frequency"]


def read_old_event(path: Path) -> dict:
    """
    Reads an old event configuration from a TOML file.

    Parameters
    ----------
    path : Path
        The directory path to the old event.

    Returns
    -------
        dict: The contents of the TOML file as a dictionary.
    """  # noqa: D401
    with open(path, "rb") as f:
        return tomli.load(f)


def river_from_charleston() -> RiverModel:
    """
    Create a RiverModel instance for the Cooper River.

    Returns
    -------
        RiverModel: A RiverModel object
        initialized with the name "Cooper River", a mean discharge of 5000 cfs,
        and specified x and y coordinates.
    """
    return RiverModel(
        name="Cooper River",
        mean_discharge=us.UnitfulDischarge(value=5000, units="cfs"),
        x_coordinate=595546.3,
        y_coordinate=3675590.6,
    )


def try_read_new_event(path: Path):
    """Try to read an EventModel from a file and return it if successful."""
    return EventFactory.load_file(path)


def copy_trackfiles(old_path: Path, new_path: Path):
    """
    Copies '.cyc' files from directories within the old path to corresponding directories in the new path.

    This function iterates over each directory in the specified old path. For each
    directory, it creates a corresponding directory in the new path if it does not
    already exist. It then copies all files with the '.cyc' extension from the old
    directory to the new directory, renaming them to match the new directory's name.

    Parameters
    ----------
    old_path: Path
        The source directory containing subdirectories with '.cyc' files.
    new_path: Path
        The destination directory where subdirectories and '.cyc' files will be copied to.
    """  # noqa: D401
    for old_event in old_path.iterdir():
        if old_event.is_dir():
            new_event = new_path / old_event.name
            new_event.mkdir(exist_ok=True, parents=True)
            for file in old_event.iterdir():
                if file.suffix == ".cyc":
                    shutil.copy(file, new_event / f"{new_event.name}.cyc")


def update_track_names(path: Path):
    """Update track names."""
    with open(path / f"{path.name}.toml", "rb") as f:
        event_set = tomli.load(f)

    for sub_event in event_set["sub_events"]:
        if sub_event["template"] == "Hurricane":
            sub_event["track_name"] = sub_event["name"]

    with open(path / f"{path.name}.toml", "wb") as f:
        tomli_w.dump(event_set, f)
