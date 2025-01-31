"""Pluvial historical events method."""

import logging
from pathlib import Path

import pandas as pd
import xarray as xr

from hydroflows._typing import EventDatesDict
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["PluvialHistoricalEvents"]

logger = logging.getLogger(__name__)


class Input(Parameters):
    """Input parameters for :py:class:`PluvialHistoricalEvents` method."""

    precip_nc: Path
    """
    The file path to the rainfall time series in NetCDF format which are used
    to derive the historical events of interest. This file should contain a time dimension
    This time series can be derived either by the
    :py:class:`hydroflows.methods.rainfall.get_ERA5_rainfall.GetERA5Rainfall`
    or can be directly supplied by the user.
    """


class Output(Parameters):
    """Output parameters for :py:class:`PluvialHistoricalEvents`."""

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
    """Parameters for :py:class:`PluvialHistoricalEvents` method."""

    events_dates: EventDatesDict
    """
    A dictionary containing event identifiers as keys and their corresponding date information as values.
    Each key is a string representing the event name (e.g., "p_event01"), and each value is another dictionary
    that holds two keys: "startdate" and "enddate". These keys map to string values that represent the
    start and end dates/times of the event, for example:

    events_dates = {
    "p_event01": {"startdate": "1995-03-04 12:00", "enddate": "1995-03-05 14:00"},
    "p_event02": {"startdate": "2005-03-04 09:00", "enddate": "2005-03-07 17:00"}
    }
    """

    event_root: Path
    """Root folder to save the derived historical events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the historical events."""

    time_dim: str = "time"
    """Time dimension of the input time series provided in :py:class:`Input` class."""


class PluvialHistoricalEvents(ExpandMethod):
    """Rule for deriving pluvial historical events from a longer series."""

    name: str = "pluvial_historical_events"

    _test_kwargs = {
        "precip_nc": Path("precip.nc"),
        "events_dates": {
            "p_event01": {
                "startdate": "1995-03-04 12:00",
                "enddate": "1995-03-05 14:00",
            },
            "p_event02": {
                "startdate": "2005-03-04 09:00",
                "enddate": "2005-03-07 17:00",
            },
        },
    }

    def __init__(
        self,
        precip_nc: Path,
        events_dates: EventDatesDict,
        event_root: Path = Path("data/events/rainfall"),
        wildcard: str = "event",
        **params,
    ) -> None:
        """Create and validate a PluvialHistoricalEvents instance.

        Parameters
        ----------
        precip_nc : Path
            The file path to the rainfall time series in NetCDF format.
        events_dates : Dict
            The dictionary mapping event names to their start and end date/time information.
        event_root : Path, optional
            The root folder to save the derived historical events, by default "data/events/rainfall".
        wildcard : str, optional
            The wildcard key for expansion over the historical events, by default "event".
        **params
            Additional parameters to pass to the PluvialHistoricalEvents instance.

        See Also
        --------
        :py:class:`PluvialHistoricalEvents Input <hydroflows.methods.rainfall.pluvial_historical_events.Input>`
        :py:class:`PluvialHistoricalEvents Output <hydroflows.methods.rainfall.pluvial_historical_events.Output>`
        :py:class:`PluvialHistoricalEvents Params <hydroflows.methods.rainfall.pluvial_historical_events.Params>`
        """
        self.params: Params = Params(
            event_root=event_root,
            events_dates=events_dates,
            wildcard=wildcard,
            **params,
        )

        self.input: Input = Input(precip_nc=precip_nc)
        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "pluvial_historical_events.yml",
        )

        self.set_expand_wildcard(wildcard, list(self.params.events_dates.keys()))

    def run(self):
        """Run the Pluvial historical events method."""
        da = xr.open_dataarray(self.input.precip_nc)
        time_dim = self.params.time_dim
        if da.ndim > 1 or time_dim not in da.dims:
            raise ValueError()

        events_list = []
        for event_name, dates in self.params.events_dates.items():
            start_time_event = dates["startdate"]
            end_time_event = dates["enddate"]

            fmt_dict = {self.params.wildcard: event_name}
            forcing_file = Path(str(self.output.event_csv).format(**fmt_dict))

            # Select the time slice for the event
            event_da = da.sel(time=slice(start_time_event, end_time_event))

            if event_da.size == 0:
                logger.warning(
                    f"Time slice for event '{event_name}' (from {start_time_event} to {end_time_event}) "
                    "returns no data.",
                    stacklevel=2,
                )
            else:
                first_date = pd.to_datetime(event_da[time_dim][0].values)
                last_date = pd.to_datetime(event_da[time_dim][-1].values)

                if first_date > start_time_event:
                    logger.warning(
                        f"The selected series for the event '{event_name}' is shorter than anticipated, as the specified start time "
                        f"of {start_time_event} is not included in the provided time series. "
                        f"The event will start from {first_date}, which is the earliest available date in the time series.",
                        stacklevel=2,
                    )

                if last_date < end_time_event:
                    logger.warning(
                        f"The selected series for the event '{event_name}' is shorter than anticipated, as the specified end time "
                        f"of {end_time_event} is not included in the provided time series. "
                        f"The event will end at {last_date}, which is the latest available date in the time series.",
                        stacklevel=2,
                    )

            event_da.to_pandas().round(2).to_csv(forcing_file)

            # save event description yaml file
            event_file = Path(str(self.output.event_yaml).format(**fmt_dict))
            event = Event(
                name=event_name,
                forcings=[{"type": "rainfall", "path": forcing_file}],
            )
            event.set_time_range_from_forcings()
            event.to_yaml(event_file)
            events_list.append({"name": event_name, "path": event_file})

        # make and save event set yaml file
        event_set = EventSet(events=events_list)
        event_set.to_yaml(self.output.event_set_yaml)
