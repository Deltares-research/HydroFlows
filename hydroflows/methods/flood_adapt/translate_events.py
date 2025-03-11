"""Translate HydroFlows events to FloodAdapt events."""

import logging
import os
import pathlib
from pathlib import Path
from typing import Union

import pandas as pd
import toml
import tomli_w
from flood_adapt import Settings
from pydantic import BaseModel

from hydroflows.events import EventSet
from hydroflows.methods.flood_adapt.convert_eventsets import (
    convert_event,
    convert_eventset,
)

# A method to translate HydroFlows events into FloodAdapt compatible events. This scripts creates a new folder including all the neccessary files (incl. timeseries csv files) to
# run the event in the FloodAdapt model. This folder must be placed into the Floodadapt input/events folder.
# NOTE: FloodAdapt does not support multiple water level stations, hence the time series can only be provided for one water level station. Only offshore models support that functionality.


class RiverModel(BaseModel):
    """Input parameters for the :py:class:`RiverModel`."""

    source: str = None
    """Source of the river discharge data. Default set to "timeseries"."""

    timeseries_file: str = None
    """File path to the river discharge time series file."""


class FloodAdaptEvent(BaseModel):
    """Input parameters for the :py:class:`FloodAdaptEvent`."""

    name: str
    """Name of the event."""

    description: str = ""
    """Description of the event."""

    mode: str = "single_event"
    """Mode of each event. Default set to "single event"."""

    template: str = "Historical"
    """FloodAdapt event template for each event. Default set to "Historical"."""

    timing: str = "historical"
    """Timing of the event. Default set to "historical"."""

    water_level_offset: dict = {}
    """Water level offset of the event."""

    wind: dict = {}
    """Dictionary of the wind. Default set to "None". """

    rainfall: dict = {}
    """Dictionary of the rainfall. Dictionary should include keys, values: source: "timeseries", timeseries_file: filepath."""

    river: list[RiverModel] = None
    """List of dictionaries of the river discharge. Each river is described in one dictionary. Dictionary should include keys, values: source: "timeseries", timeseries_file: filepath. """

    time: dict = {}
    """Timeframe of the event"""

    tide: dict = {}
    """Dictionary of the tide. Dictionary should include keys, values: source: "timeseries", timeseries_file: filepath."""

    surge: dict = {}
    """Dictionary of the wind. Default set to "None". """

    @property
    def attrs(self) -> dict:
        """
        Returns all attributes of the class as a dictionary.

        Returns
        -------
        dict
            A dictionary containing all the attributes of the FloodAdapt instance.
        """
        return self.model_dump(exclude_none=True)

    def create_tide_file(self) -> pd.DataFrame:
        """
        Create a tide file for a FloodAdaptEvent if no water level os provided.

        Parameters
        ----------
        fa_event : FloodAdaptEvent
            The FloodAdaptEvent object to create the tide file for.

        Returns
        -------
        df_tide : pd.DataFrame
            A DataFrame with a "time" column (datetime64[ns] dtype) and a "tide" column (float64 dtype) with all values set to 0.
        """
        start = self.time["start_time"]
        end = self.time["end_time"]
        df_tide = pd.DataFrame()
        df_tide["time"] = pd.date_range(start=start, end=end, freq="h")
        df_tide["tide"] = 0

        return df_tide

    @staticmethod
    def read_csv_stations(filepath: Union[str, Path]) -> list:
        """
        Read a CSV file containing station data and returns a list of stations.

        The CSV file is expected to have either two columns or more. The first column must be the timestamp of the timeseries.
        If the CSV file contains more than one station, individual DataFrames for each station are returned with keys in the format "station_{column_name}".

        Parameters
        ----------
        filepath : Union[str, Path]
            The path to the CSV file containing the station data.

        Returns
        -------
        list
            A list of DataFrames where each DataFrame represents station data.
        """
        df_stations = pd.read_csv(filepath)
        all_stations = {}
        if len(df_stations.columns) == 2:
            all_stations[df_stations.columns[1]] = df_stations.iloc[
                0:, 1
            ]  # df_stations
            return all_stations
        else:
            # Write individual files
            df_stations.set_index(df_stations.columns[0], inplace=True, drop=True)
            for column in df_stations.columns:
                df_station = df_stations[column]
                all_stations[f"station_{column}"] = df_station
            return all_stations


class ForcingSources:
    """Input parameters for the :py:class:`ForcingSources`."""

    def __init__(
        self,
        rainfall: Union[str, Path] = None,
        water_level: Union[str, Path] = None,
        discharge: Union[str, Path] = None,
    ) -> None:
        """
        Initialize ForcingSources object.

        Sets all forcing sources to None. These include rainfall, water level and discharge.

        Parameters
        ----------
        rainfall : Union[str, Path], optional
            The file path to the rainfall data.
        water_level : Union[str, Path], optional
            The file path to the water_level data.
        discharge : Union[str, Path], optional
            The file path to the river discharge data.
        """
        self.rainfall = rainfall
        self.water_level = water_level
        self.discharge = discharge


def translate_events(
    root: Union[str, Path] = None,
    fa_events: Union[str, Path] = None,
    description: str = "This is a hydroflows event set",
):
    """
    Translate HydroFlows events to floodAdapt events.

    Parameters
    ----------
    root : Union[str, Path]
        Path to the root folder of the events, by default None
    fa_events : Union[str, Path]
        Folder to write the floodadapt events to, by default None
    """
    # Create output directory
    fn_floodadapt = Path.joinpath(fa_events, root.stem)
    fn_floodadapt.parent.mkdir(parents=True, exist_ok=True)

    # Get events
    events = EventSet.from_yaml(root)

    # Set variables for function
    if len(events.events) > 1:
        subevent_name = []
        rp = []

    forcing_sources = ForcingSources()

    for event_dict in events.events:
        name = event_dict["name"]
        file_name = event_dict["path"].stem
        event = events.get_event(name)
        event.read_forcing_data()
        tstart = event.tstart
        tstop = event.tstop
        forcings = event.forcings

        # Create dictionary for floodadapt individual event
        fa_event = FloodAdaptEvent(
            name=file_name,
            description=description,
        )

        # Time
        fa_event.time["start_time"] = str(tstart).replace(":", "").replace("-", "")
        fa_event.time["end_time"] = str(tstop).replace(":", "").replace("-", "")

        # Forcings
        for i in forcings:
            # Rainfall
            if "rainfall" not in i.type and forcing_sources.rainfall is None:
                fa_event.rainfall["source"] = "none"
                fa_event.rainfall["increase"] = 0.0
            elif forcing_sources.rainfall is not None:
                pass
            else:
                forcing_sources.rainfall = i.path.as_posix()
                fa_event.rainfall["source"] = "timeseries"
                fa_event.rainfall[
                    "timeseries_file"
                ] = f"{Path(forcing_sources.rainfall).stem}.csv"
            # Water level
            if "water_level" not in i.type and forcing_sources.water_level is None:
                fa_event.tide["source"] = "timeseries"
                forcing_sources.water_level = "synthetic"
                df_tide = fa_event.create_tide_file()
                fa_event.tide["timeseries_file"] = "tide.csv"
            elif (
                forcing_sources.water_level is not None
                and forcing_sources.water_level != "synthetic"
            ):
                pass
            else:
                forcing_sources.water_level = i.path.as_posix()
                csv_station_timeseries_waterlevel = fa_event.read_csv_stations(
                    forcing_sources.water_level
                )
                if len(csv_station_timeseries_waterlevel) == 1:
                    fa_event.tide["source"] = "timeseries"
                    fa_event.tide[
                        "timeseries_file"
                    ] = f"{Path(forcing_sources.water_level).stem}.csv"
                else:
                    logging.error(
                        "FloodAdapt does not support more than one water level."
                    )
                    return
                    # NOTE: More than one water level location are not supported in FA (possibly in offshore models only)
                    # for key, value in csv_station_timeseries_waterlevel.items():
                    #    fa_event.tide[key] = {}
                    #    fa_event.tide[key]["source"] = "timeseries"
                    #    fa_event.tide[key]["timeseries_file"] = f"{key}.csv"

            fa_event.water_level_offset["value"] = 0
            fa_event.water_level_offset["units"] = "feet"

            # RiverModel
            if "discharge" not in i.type and forcing_sources.discharge is None:
                fa_event.river = []
            elif forcing_sources.discharge is not None:
                pass
            else:
                river = []
                forcing_sources.discharge = i.path.as_posix()
                rivers = RiverModel(source="timeseries")
                csv_station_timeseries_discharge = fa_event.read_csv_stations(
                    forcing_sources.discharge
                )
                for key in csv_station_timeseries_discharge:
                    rivers.timeseries_file = f"{key}.csv"
                    river.append(rivers.model_dump())
                fa_event.river = river

        if len(events.events) > 1:
            return_period = 1 / event.return_period

        # Surge
        fa_event.surge["source"] = "none"
        fa_event.surge["shape_type"] = "gaussian"

        # Wind
        fa_event.wind["source"] = "none"

        # Write final toml or dict.
        event_fn = pathlib.Path.joinpath(fn_floodadapt, file_name)
        if not os.path.exists(event_fn):
            os.makedirs(event_fn)

        with open(os.path.join(event_fn, f"{file_name}.toml"), "wb") as f:
            tomli_w.dump(fa_event.attrs, f)

        # Copy dataset into folder
        if forcing_sources.rainfall is not None:
            df_rain = pd.read_csv(forcing_sources.rainfall)
            df_rain.to_csv(
                event_fn / fa_event.rainfall["timeseries_file"],
                index=False,
                header=None,
            )
        if forcing_sources.water_level is not None:
            if "synthetic" in forcing_sources.water_level:
                df_tide.to_csv(event_fn / "tide.csv", index=False, header=None)
            elif len(csv_station_timeseries_waterlevel) == 1:
                df_tide = pd.read_csv(forcing_sources.water_level)
                df_tide.to_csv(
                    event_fn / fa_event.tide["timeseries_file"],
                    index=False,
                    header=None,
                )
            else:
                for key, value in csv_station_timeseries_waterlevel.items():
                    value.to_csv(
                        os.path.join(event_fn, f"{key}.csv"), index=False, header=None
                    )
        if forcing_sources.discharge is not None:
            if len(csv_station_timeseries_discharge) == 1:
                df_discharge = pd.read_csv(forcing_sources.discharge)
                df_discharge.to_csv(
                    event_fn / fa_event.river[0]["timeseries_file"],
                    index=False,
                    header=None,
                )
            else:
                for key, value in csv_station_timeseries_discharge.items():
                    df = value
                    df = df.round(decimals=2)
                    df.to_csv(os.path.join(event_fn, f"{key}.csv"), header=None)

        # Save return period for test set toml
        if len(events.events) > 1:
            rp.append(return_period)
            subevent_name.append(file_name)

            # reset everything to None
            forcing_sources.rainfall = None
            forcing_sources.water_level = None
            forcing_sources.discharge = None

    # Create dictionary for floodadapt for test set
    if len(events.events) > 1:
        name_test_set = root.stem

        floodadapt_config = {
            "name": name_test_set,
            "description": description,
            "mode": "risk",
            "subevent_name": subevent_name,
            "frequency": rp,
        }

        # Write final toml or dict.
        with open(
            os.path.join(fn_floodadapt, f"{name_test_set}.toml"), "w"
        ) as toml_file:
            toml.dump(floodadapt_config, toml_file)
    # Convert event
    # Set up Database
    Settings(
        DATABASE_ROOT=Path(r"C:\Users\rautenba\repos\Database"),
        DATABASE_NAME="charleston_test",
        SYSTEM_FOLDER=Path(r"C:\Users\rautenba\repos\Database\system"),
    )
    if len(events.events) > 1:
        convert_eventset(
            Path(fn_floodadapt),
            Path(
                r"C:\Users\rautenba\repos\Database\charleston_test\input\events\Probabilistic_set"
            ),
        )
    else:
        convert_event(fa_event.attrs, Path(event_fn))
