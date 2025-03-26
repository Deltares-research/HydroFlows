"""Method to derive historical events with one or more drivers from timeseries data."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import xarray as xr
from pydantic import model_validator

from hydroflows._typing import EventDatesDict, FileDirPath, OutputDirPath
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["HistoricalEvents", "Input", "Output", "Params"]

logger = logging.getLogger(__name__)


class Input(Parameters):
    """Input parameters for the :py:class:`HistoricalEvents` method."""

    discharge_nc: Optional[Path] = None
    """The file path to the discharge time series in NetCDF format which is used
    to derive historical events. This file should contain a time and an index
    dimension, specified by the `discharge_index_dim` parameter, for
    several (gauge) locations.

    The discharge time series can be produced either by the Wflow toolchain (via the
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowBuild`,
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing`, and
    :py:class:`hydroflows.methods.wflow.wflow_run.WflowRun` methods) or can be directly supplied by the user.
    """

    precip_nc: Optional[Path] = None
    """
    The file path to the rainfall time series in NetCDF format which are used
    to derive the historical events of interest. This file should contain a time dimension.
    These time series can be derived either by the
    :py:class:`hydroflows.methods.rainfall.get_ERA5_rainfall.GetERA5Rainfall`
    or can be directly supplied by the user.
    """

    water_level_nc: Optional[Path] = None
    """
    The file path to the water level time series in NetCDF format which are used
    to derive the historical events of interest. This file should contain a time and an index
    dimension specified by the `water_level_index_dim` parameter for several locations.

    The water level time series can be produced either after processing GTSM tide and surge data
    (can be obtained by the :py:class:`hydroflows.methods.coastal.get_gtsm_data.GetGTSMData` method)
    or can be directly supplied by the user.
    """

    @model_validator(mode="after")
    def _validate_model(self):
        if (
            self.discharge_nc is None
            and self.precip_nc is None
            and self.water_level_nc is None
        ):
            raise ValueError("At least one of the input files should be provided.")


class Output(Parameters):
    """Output parameters for the :py:class:`HistoricalEvents` method."""

    event_yaml: FileDirPath
    """The path to the event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_set_yaml: Path
    """The path to the event set yml file,
    see also :py:class:`hydroflows.events.EventSet`."""


class Params(Parameters):
    """Parameters for :py:class:`HistoricalEvents` method."""

    events_dates: EventDatesDict
    """
    A dictionary containing event identifiers as keys and their corresponding date information as values.
    Each key is a string representing the event name (e.g., "historical_event01"), and each value is another dictionary
    that holds two keys: "startdate" and "enddate". These keys map to string values that represent the
    start and end dates/times of the event, for example:

    events_dates = {
    "historical_event01": {"startdate": "1995-03-04 12:00", "enddate": "1995-03-05 14:00"},
    }
    """

    output_dir: OutputDirPath
    """Directory to save the derived historical events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the historical events."""

    discharge_index_dim: str = "Q_gauges"
    """Index dimension of the discharge input time series provided in :py:class:`Input` class."""

    water_level_index_dim: str = "wl_locs"
    """Index dimension of the water level input time series provided in :py:class:`Input` class."""

    time_dim: str = "time"
    """Time dimension of the input time series provided in :py:class:`Input` class."""


class HistoricalEvents(ExpandMethod):
    """Method to derive historical events with one or more drivers from timeseries data.

    Parameters
    ----------
    discharge_nc : Path, optional
        The file path to the discharge time series in NetCDF format.
    precip_nc : Path, optional
        The file path to the rainfall time series in NetCDF format.
    water_level_nc : Path, optional
        The file path to the water level time series in NetCDF format.
    events_dates : Dict
        The dictionary mapping event names to their start and end date/time information. For example,
        events_dates = {"p_event": {"startdate": "1995-03-04 12:00", "enddate": "1995-03-05 14:00"}.
    output_dir : Path, optional
        The directory where the derived historical events will be saved, by default "data/historical_events".
    wildcard : str, optional
        The wildcard key for expansion over the historical events, by default "event".
    **params
        Additional parameters to pass to the HistoricalEvents instance.

    See Also
    --------
    :py:class:`HistoricalEvents Input <hydroflows.methods.historical_events.historical_events.Input>`
    :py:class:`HistoricalEvents Output <hydroflows.methods.historical_events.historical_events.Output>`
    :py:class:`HistoricalEvents Params <hydroflows.methods.historical_events.historical_events.Params>`
    """

    name: str = "historical_events"

    _test_kwargs = {
        "discharge_nc": Path("discharge.nc"),
        "precip_nc": Path("precip.nc"),
        "water_level_nc": Path("water_level.nc"),
        "events_dates": {
            "historical_event01": {
                "startdate": "2000-01-02 00:00",
                "enddate": "2000-01-24 12:00",
            },
        },
    }

    def __init__(
        self,
        events_dates: EventDatesDict,
        discharge_nc: Path = None,
        precip_nc: Path = None,
        water_level_nc: Path = None,
        output_dir: Path = Path("data/historical_events"),
        wildcard: str = "event",
        **params,
    ) -> None:
        self.params: Params = Params(
            output_dir=output_dir,
            events_dates=events_dates,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(
            discharge_nc=discharge_nc,
            precip_nc=precip_nc,
            water_level_nc=water_level_nc,
        )

        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.output_dir / f"{wc}.yml",
            event_set_yaml=self.params.output_dir / "historical_events.yml",
        )

        self.set_expand_wildcard(wildcard, list(self.params.events_dates.keys()))

    def _run(self):
        """Run the HistoricalEvents method."""
        # Possible input files and their corresponding index dimensions
        event_files = {}
        if self.input.discharge_nc is not None:
            event_files["discharge"] = (
                self.input.discharge_nc,
                self.params.discharge_index_dim,
            )
        if self.input.precip_nc is not None:
            event_files["rainfall"] = (self.input.precip_nc, None)
        if self.input.water_level_nc is not None:
            event_files["water_level"] = (
                self.input.water_level_nc,
                self.params.water_level_index_dim,
            )

        # Dictionary to store the input time series
        da_dict = {}
        time_dim = self.params.time_dim

        # Loop through the event files, read the input time series and append them to the dictionary
        for event_type, (file_path, index_dim) in event_files.items():
            da = xr.open_dataarray(file_path)
            da_dict[event_type] = da
            dims_to_check = [time_dim]
            if index_dim:
                dims_to_check.append(index_dim)
            for dim in dims_to_check:
                if dim not in da.dims:
                    raise ValueError(f"{dim} not a dimension in {file_path}")
            if event_type == "rainfall" and (da.ndim > 1 or time_dim not in da.dims):
                raise ValueError(f"Invalid dimensions in {file_path}")

        # Loop through the events and save the event csv/yaml files and the event set
        events_list = []
        for event_name, dates in self.params.events_dates.items():
            output = self.get_output_for_wildcards({self.params.wildcard: event_name})
            event_start_time = dates["startdate"]
            event_end_time = dates["enddate"]

            forcings_list = []
            event_file = output["event_yaml"]
            for event_type, da_driver in da_dict.items():
                event_data = da_driver.sel(time=slice(event_start_time, event_end_time))
                if event_data.size == 0:
                    logger.warning(
                        f"Time slice for event '{event_name}' (for driver {event_type} from {event_start_time} to {event_end_time}) "
                        "returns no data. Skipping this driver for this event.",
                        stacklevel=2,
                    )
                    continue
                else:
                    first_date = pd.to_datetime(event_data[time_dim][0].values)
                    last_date = pd.to_datetime(event_data[time_dim][-1].values)

                    if first_date > event_start_time:
                        logger.warning(
                            f"The selected series for the event '{event_name}' (driver {event_type}) is shorter than anticipated, as the specified start time "
                            f"of {event_start_time} is not included in the provided time series. "
                            f"The event will start from {first_date}, which is the earliest available date in the time series.",
                            stacklevel=2,
                        )

                    if last_date < event_end_time:
                        logger.warning(
                            f"The selected series for the event '{event_name}' (driver {event_type}) is shorter than anticipated, as the specified end time "
                            f"of {event_end_time} is not included in the provided time series. "
                            f"The event will end at {last_date}, which is the latest available date in the time series.",
                            stacklevel=2,
                        )

                forcing_file = Path(
                    event_file.parent, f"{event_file.stem}_{event_type}.csv"
                )
                event_data.to_pandas().round(2).to_csv(forcing_file)
                forcings_list.append({"type": event_type, "path": forcing_file})

            # save event description yaml file
            event = Event(
                name=event_name,
                forcings=forcings_list,
            )
            event.set_time_range_from_forcings()
            event.to_yaml(event_file)
            events_list.append({"name": event_name, "path": event_file})

        # make and save event set yaml file
        event_set = EventSet(events=events_list)
        event_set.to_yaml(self.output.event_set_yaml)
