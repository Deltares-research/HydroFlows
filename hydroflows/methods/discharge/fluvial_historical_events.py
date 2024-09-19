"""Fluvial historical events method."""
import warnings
from pathlib import Path

import pandas as pd
import xarray as xr

from hydroflows._typing import EventDatesDict
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["FluvialHistoricalEvents"]


class Input(Parameters):
    """Input parameters for the :py:class:`FluvialHistoricalEvents` method."""

    discharge_nc: Path
    """The file path to the discharge time series in NetCDF format which is used
    to derive historical events. This file contains an index dimension and a time
    dimension for several Sfincs boundary points.
    - The index dimension corresponds to the index of the Sfincs source points, providing the corresponding time
      series at specific locations.
    - This time series can be produced either by the Wflow toolchain (via the
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowBuild`,
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing`, and
    :py:class:`hydroflows.methods.wflow.wflow_run.WflowRun` methods) or can be directly supplied by the user.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`FluvialHistoricalEvents` method."""

    event_yaml: Path
    """The path to the event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_csv: Path
    """The path to the event csv timeseries file."""

    event_set_yaml: Path
    """The path to the event set yml file that contains the derived
    fluvial event configurations. This event set can be created from
    a dictionary using the :py:class:`hydroflows.events.EventSet` class.
    """


class Params(Parameters):
    """Parameters for :py:class:`FluvialHistoricalEvents` method."""

    events_dates: EventDatesDict
    """
    A dictionary containing event identifiers as keys and their corresponding date information as values.
    Each key is a string representing the event name (e.g., "q_event01"), and each value is another dictionary
    that holds two keys: "startdate" and "enddate". These keys map to string values that represent the
    start and end dates/times of the event, for example:
    events_dates = {
    "q_event01": {"startdate": "1995-03-04 12:00", "enddate": "1995-03-05 14:00"},
    "q_event02": {"startdate": "2005-03-04 09:00", "enddate": "2005-03-07 17:00"}
    }
    """

    event_root: Path
    """Root folder to save the derived historical events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the historical events."""

    index_dim: str = "Q_gauges"
    """Index dimension of the input time series provided in :py:class:`Input` class."""

    time_dim: str = "time"
    """Time dimension of the input time series provided in :py:class:`Input` class."""


class FluvialHistoricalEvents(ExpandMethod):
    """Rule for deriving fluvial historical events from a longer series."""

    name: str = "fluvial_historical_events"

    _test_kwargs = {
        "discharge_nc": Path("discharge.nc"),
        "events_dates": {
            "q_event01": {
                "startdate": "1995-03-04 12:00",
                "enddate": "1995-03-05 14:00",
            },
            "q_event02": {
                "startdate": "2005-03-04 09:00",
                "enddate": "2005-03-07 17:00",
            },
        },
    }

    def __init__(
        self,
        discharge_nc: Path,
        events_dates: EventDatesDict,
        event_root: Path = Path("data/events/discharge"),
        wildcard: str = "event",
        **params,
    ) -> None:
        """Create and validate a FluvialHistoricalEvents instance.

        Parameters.
        ----------
        discharge_nc : Path
            The file path to the discharge time series in NetCDF format.
        event_dates : Dict
            The dictionary mapping event names to their start and end date/time information.
        event_root : Path, optional
            The root folder to save the derived historical events, by default "data/events/discharge".
        wildcard : str, optional
            The wildcard key for expansion over the historical events, by default "event".
        **params
            Additional parameters to pass to the FluvialHistoricalEvents Params instance.
            See :py:class:`fluvial_historical_events Params <hydroflows.methods.discharge.fluvial_historical_events.Params>`.

        See Also
        --------
        :py:class:`FluvialHistoricalEvents Input <hydroflows.methods.discharge.fluvial_historical_events.Input>`
        :py:class:`FluvialHistoricalEvents Output <hydroflows.methods.discharge.fluvial_historical_events.Output>`
        :py:class:`FluvialHistoricalEvents Params <hydroflows.methods.discharge.fluvial_historical_events.Params>`
        """
        self.params: Params = Params(
            event_root=event_root,
            events_dates=events_dates,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(discharge_nc=discharge_nc)
        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "fluvial_events.yml",
        )

        self.set_expand_wildcard(wildcard, list(self.params.events_dates.keys()))

    def run(self):
        """Run the FluvialHistoricalEvents method."""
        # read the provided time series
        da = xr.open_dataarray(self.input.discharge_nc)
        time_dim = self.params.time_dim
        index_dim = self.params.index_dim
        # check if dims in da
        for dim in [time_dim, index_dim]:
            if dim not in da.dims:
                raise ValueError(f"{dim} not a dimension in, {self.input.discharge_nc}")

        events_list = []
        for event_name, dates in self.params.events_dates.items():
            start_time_event = dates["startdate"]
            end_time_event = dates["enddate"]

            fmt_dict = {self.params.wildcard: event_name}
            forcing_file = Path(str(self.output.event_csv).format(**fmt_dict))

            # slice data
            event_data = da.sel(time=slice(start_time_event, end_time_event))

            if event_data.size == 0:
                warnings.warn(
                    f"Time slice for event '{event_name}' (from {start_time_event} to {end_time_event}) "
                    "returns no data.",
                    stacklevel=2,
                )
            else:
                first_date = pd.to_datetime(event_data[time_dim][0].values)
                last_date = pd.to_datetime(event_data[time_dim][-1].values)

                if first_date > start_time_event:
                    warnings.warn(
                        f"The selected series for the event '{event_name}' is shorter than anticipated, as the specified start time "
                        f"of {start_time_event} is not included in the provided time series. "
                        f"The event will start from {first_date}, which is the earliest available date in the time series.",
                        stacklevel=2,
                    )

                if last_date < end_time_event:
                    warnings.warn(
                        f"The selected series for the event '{event_name}' is shorter than anticipated, as the specified end time "
                        f"of {end_time_event} is not included in the provided time series. "
                        f"The event will end at {last_date}, which is the latest available date in the time series.",
                        stacklevel=2,
                    )

            event_data.to_pandas().round(2).to_csv(forcing_file)

            # save event description yaml file
            event_file = Path(str(self.output.event_yaml).format(**fmt_dict))
            event = Event(
                name=event_name,
                forcings=[{"type": "discharge", "path": forcing_file}],
            )
            event.set_time_range_from_forcings()
            event.to_yaml(event_file)
            events_list.append({"name": event_name, "path": event_file})

        # make and save event set yaml file
        event_set = EventSet(events=events_list)
        event_set.to_yaml(self.output.event_set_yaml)
