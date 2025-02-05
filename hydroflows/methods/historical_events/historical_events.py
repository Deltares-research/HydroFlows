"""Historical events method for all drivers."""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import xarray as xr
from pydantic import model_validator

from hydroflows._typing import EventInfoDict
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["HistoricalEvents"]

logger = logging.getLogger(__name__)


class Input(Parameters):
    """Input parameters for the :py:class:`HistoricalEvents` method."""

    discharge_nc: Optional[Path] = None
    """The file path to the discharge time series in NetCDF format which is used
    to derive historical events. This file should contain a time and an index
    dimension for several (gauge) locations.

    The discharge time series can be produced either by the Wflow toolchain (via the
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowBuild`,
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing`, and
    :py:class:`hydroflows.methods.wflow.wflow_run.WflowRun` methods) or can be directly supplied by the user.

    In case of forcing the historical discharge events in Sfincs using the
    :py:class:`hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing` method,
    the index dimension should correspond to the index of the Sfincs source points, providing the corresponding
    time series at specific locations.
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
    dimension for several locations.

    The water level time series can be produced either after processing GTSM tide and surge data
    (can be obtained by the :py:class:`hydroflows.methods.coastal.get_gtsm_data.GetGTSMData` method)
    or can be directly supplied by the user.

    In case of forcing the historical water level events in Sfincs using the
    :py:class:`hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing` method,
    the index dimension should correspond to the index of the Sfincs bnd points, providing the corresponding
    time series at specific locations.
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

    event_yaml: Path
    """The path to the event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_csv: Path
    """The path to the event csv timeseries file"""

    event_set_yaml: Path
    """The path to the event set yml file,
    see also :py:class:`hydroflows.events.EventSet`.
    """


class Params(Parameters):
    """Parameters for :py:class:`HistoricalEvents` method."""

    events_info: EventInfoDict
    """
    A dictionary containing event identifiers as keys and their corresponding date and event
    type information as values.
    Each key is a string representing the event name (e.g., "p_event01"), and each value is another dictionary
    that holds three keys: "startdate", "enddate" and "type". The first two keys map to string values that represent the
    start and end dates/times of the event, while the third one defines the type of the
    historical event, i.e. "water_level", "discharge" or "rainfall", for example:

    events_info = {
    "p_event": {"startdate": "1995-03-04 12:00", "enddate": "1995-03-05 14:00", "type": "rainfall"},
    "wl_event": {"startdate": "2005-03-04 09:00", "enddate": "2005-03-07 17:00", "type": "water_level"},
    "q_event": {"startdate": "2010-03-04 09:00", "enddate": "2010-03-07 17:00", "type": "discharge"}
    }
    """

    event_root: Path
    """Root folder to save the derived historical events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the historical events."""

    discharge_index_dim: str = "Q_gauges"
    """Index dimension of the discharge input time series provided in :py:class:`Input` class."""

    water_level_index_dim: str = "wl_locs"
    """Index dimension of the water level input time series provided in :py:class:`Input` class."""

    time_dim: str = "time"
    """Time dimension of the input time series provided in :py:class:`Input` class."""


class HistoricalEvents(ExpandMethod):
    """Rule for deriving historical events from a longer series."""

    name: str = "historical_events"

    _test_kwargs = {
        "discharge_nc": Path("discharge.nc"),
        "precip_nc": Path("precip.nc"),
        "events_info": {
            "q_event01": {
                "startdate": "1995-03-04 12:00",
                "enddate": "1995-03-05 14:00",
                "type": "discharge",
            },
            "q_event02": {
                "startdate": "2005-03-04 09:00",
                "enddate": "2005-03-07 17:00",
                "type": "discharge",
            },
            "p_event01": {
                "startdate": "1995-03-04 12:00",
                "enddate": "1995-03-05 14:00",
                "type": "rainfall",
            },
        },
    }

    def __init__(
        self,
        events_info: EventInfoDict,
        discharge_nc: Path = None,
        precip_nc: Path = None,
        water_level_nc: Path = None,
        event_root: Path = Path("data/historical_events"),
        wildcard: str = "event",
        **params,
    ) -> None:
        """Create and validate a HistoricalEvents instance.

        Parameters
        ----------
        discharge_nc : Path, optional
            The file path to the discharge time series in NetCDF format.
        precip_nc : Path, optional
            The file path to the rainfall time series in NetCDF format.
        water_level_nc : Path, optional
            The file path to the water level time series in NetCDF format.
        events_info : Dict
            The dictionary mapping event names to their start/end time, as well as the event type
            (i.e. "water_level", "discharge" or "rainfall") information. For example,
            events_info = {"p_event": {"startdate": "1995-03-04 12:00", "enddate": "1995-03-05 14:00", "type": "rainfall"}.
        event_root : Path, optional
            The root folder to save the derived historical events, by default "data/historical_events".
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
        self.params: Params = Params(
            event_root=event_root,
            events_info=events_info,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(
            discharge_nc=discharge_nc,
            precip_nc=precip_nc,
            water_level_nc=water_level_nc,
        )

        for event_name, event_info in self.params.events_info.items():
            if event_info["type"] == "discharge":
                if self.input.discharge_nc is None:
                    raise ValueError(
                        f"Discharge time series file should be provided for event {event_name}."
                    )
            elif event_info["type"] == "rainfall":
                if self.input.precip_nc is None:
                    raise ValueError(
                        f"Precipitation time series file should be provided for event {event_name}."
                    )
            elif event_info["type"] == "water_level":
                if self.input.water_level_nc is None:
                    raise ValueError(
                        f"Water level time series file should be provided for event {event_name}."
                    )

        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "historical_events.yml",
        )

        self.set_expand_wildcard(wildcard, list(self.params.events_info.keys()))

    def run(self):
        """Run the HistoricalEvents method."""
        # Get the event types from the events_info. This returns only unique values
        event_types = {
            event_info["type"] for event_info in self.params.events_info.values()
        }
        time_dim = self.params.time_dim

        # Dictionary to store the input time series
        da_dict = {}

        # Possible input files and their corresponding index dimensions
        event_files = {
            "discharge": (self.input.discharge_nc, self.params.discharge_index_dim),
            "rainfall": (self.input.precip_nc, None),
            "water_level": (
                self.input.water_level_nc,
                self.params.water_level_index_dim,
            ),
        }

        # Loop through the event files and read the input time series
        for event_type, (file_path, index_dim) in event_files.items():
            if event_type in event_types:
                da = xr.open_dataarray(file_path)
                da_dict[event_type] = da
                dims_to_check = [time_dim]
                if index_dim:
                    dims_to_check.append(index_dim)
                for dim in dims_to_check:
                    if dim not in da.dims:
                        raise ValueError(f"{dim} not a dimension in {file_path}")
                if event_type == "rainfall" and (
                    da.ndim > 1 or time_dim not in da.dims
                ):
                    raise ValueError(f"Invalid dimensions in {file_path}")

        # Loop through the events and save the event csv/yaml files and the event set
        events_list = []
        for event_name, event_info in self.params.events_info.items():
            event_start_time = event_info["startdate"]
            event_end_time = event_info["enddate"]

            fmt_dict = {self.params.wildcard: event_name}
            forcing_file = Path(str(self.output.event_csv).format(**fmt_dict))

            # slice data
            event_data = da_dict[event_info["type"]].sel(
                time=slice(event_start_time, event_end_time)
            )

            if event_data.size == 0:
                logger.warning(
                    f"Time slice for event '{event_name}' (from {event_start_time} to {event_end_time}) "
                    "returns no data.",
                    stacklevel=2,
                )
            else:
                first_date = pd.to_datetime(event_data[time_dim][0].values)
                last_date = pd.to_datetime(event_data[time_dim][-1].values)

                if first_date > event_start_time:
                    logger.warning(
                        f"The selected series for the event '{event_name}' is shorter than anticipated, as the specified start time "
                        f"of {event_start_time} is not included in the provided time series. "
                        f"The event will start from {first_date}, which is the earliest available date in the time series.",
                        stacklevel=2,
                    )

                if last_date < event_end_time:
                    logger.warning(
                        f"The selected series for the event '{event_name}' is shorter than anticipated, as the specified end time "
                        f"of {event_end_time} is not included in the provided time series. "
                        f"The event will end at {last_date}, which is the latest available date in the time series.",
                        stacklevel=2,
                    )

            event_data.to_pandas().round(2).to_csv(forcing_file)

            # save event description yaml file
            event_file = Path(str(self.output.event_yaml).format(**fmt_dict))
            event = Event(
                name=event_name,
                forcings=[{"type": event_info["type"], "path": forcing_file}],
            )
            event.set_time_range_from_forcings()
            event.to_yaml(event_file)
            events_list.append({"name": event_name, "path": event_file})

        # make and save event set yaml file
        event_set = EventSet(events=events_list)
        event_set.to_yaml(self.output.event_set_yaml)
