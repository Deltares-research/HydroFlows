"""Future climate rainfall method."""

import os
from pathlib import Path
from typing import List, Optional

import pandas as pd
from pydantic import PositiveInt, model_validator

from hydroflows._typing import ListOfStr
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters


class Input(Parameters):
    """Input parameters for the :py:class:`FutureClimateRainfall` method."""

    event_set_yaml: Path
    """The file path to the event set YAML file, which includes the events to be scaled
    for future climate projections, see also :py:class:`hydroflows.events.EventSet`."""


class Output(Parameters):
    """Output parameters for the :py:class:`FutureClimateRainfall` method."""

    future_event_yaml: Path
    """The path to the scaled event description file,
    see also :py:class:`hydroflows.events.Event`."""

    future_event_csv: Path
    """The path to the scaled event csv timeseries file"""

    future_event_set_yaml: Path
    """The path to the scaled event set yml file,
    see also :py:class:`hydroflows.events.EventSet`.
    """


class Params(Parameters):
    """Parameters for :py:class:`FutureClimateRainfall` method."""

    future_period: PositiveInt
    """The future time period of interest for which CC scaling is applied."""

    scenario_name: str
    """Future scenario name for which CC scaling is applied."""

    dT: float
    """Temperature change corresponding to the `future_period` and `scenario_name`
    relative to a reference period.

    Temperature changes for different periods and emission scenarios
    for CMIP5 and CMIP6 models can be taken via:
    `Future Climate Data Platform <https://dap.climateinformation.org/dap/>`_"""

    ref_year: PositiveInt
    """Reference historical year for which the change of temperature `dT` is relative for."""

    alpha: float = 7
    """The rate of change of precipitation with respect to temperature (in % per degree)
    used in Clausius-Clapeyron (CC) scaling"""

    design_event_year: int = None
    """Design event representing year in case of scaling a design event.
    Used to estimate the temperature change on this year by linearly interpolating
    between the reference year `ref_year` and the future projection period `future_period`."""

    event_root: Optional[Path] = None
    """Root folder to save the derived scaled events."""

    wildcard: str = "future_event"
    """The wildcard key for expansion over the scaled events."""

    event_input_names: Optional[ListOfStr] = None

    time_col: str = "time"
    """Time column name per event csv file."""

    @model_validator(mode="after")
    def _validate_model(self):
        if self.event_root is None:
            self.event_root = (
                f"data/events/future_rainfall/{self.scenario_name}_{self.future_period}"
            )
        if self.future_period <= self.ref_year:
            raise ValueError(
                "The provided future time period cannot be earlier than the reference year."
            )


class FutureClimateRainfall(ExpandMethod):
    """Rule for deriving future climate rainfall by scaling an event using Clausius-Clapeyron (CC)."""

    name: str = "future_climate_rainfall"

    _test_kwargs = {
        "future_period": 2085,
        "scenario_name": "RCP85",
        "dT": 1.8,
        "ref_year": 1990,
        "event_set_yaml": Path("event_set.yaml"),
    }

    def __init__(
        self,
        future_period: str,
        scenario_name: str,
        dT: int,
        ref_year: int,
        event_set_yaml: Path,
        event_root: Optional[Path] = None,
        wildcard: str = "future_event",
        event_input_names: Optional[List[str]] = None,
        **params,
    ) -> None:
        """Create and validate a FutureClimateRainfall instance.

        Parameters
        ----------
        event_set_yaml : Path
            The file path to the event set YAML file, which includes the events to be scaled
            for a future climate projection.
        future_period: str
            The future time period of interest for which CC scaling is applied.
        scenario_name: str
            Future scenario name for which CC scaling is applied.
        dT: float
            Temperature change value for the respective emission scenario name `scenario_name` and period
            `future_period` relative to a reference period `ref_year`.
        ref_year: int
            Reference historical year for which the change of temperature `dT` is relative for.
        **params
            Additional parameters to pass to the FutureClimateRainfall Params instance.

        See Also
        --------
        :py:class:`FutureClimateRainfall Input <hydroflows.methods.rainfall.future_climate_rainfall.Input>`
        :py:class:`FutureClimateRainfall Output <hydroflows.methods.rainfall.future_climate_rainfall.Output>`
        :py:class:`FutureClimateRainfall Params <hydroflows.methods.rainfall.future_climate_rainfall.Params>`
        """
        self.params: Params = Params(
            future_period=future_period,
            scenario_name=scenario_name,
            dT=dT,
            ref_year=ref_year,
            event_root=event_root,
            wildcard=wildcard,
            event_input_names=event_input_names,
            **params,
        )

        self.input: Input = Input(event_set_yaml=event_set_yaml)

        wc = "{" + self.params.wildcard + "}"

        self.output: Output = Output(
            future_event_yaml=Path(self.params.event_root) / f"{wc}.yml",
            future_event_csv=Path(self.params.event_root) / f"{wc}.csv",
            future_event_set_yaml=Path(self.params.event_root)
            / f"future_pluvial_events_{self.params.scenario_name}_{self.params.future_period}.yml",
        )

        future_event_names_list = []
        if self.params.event_input_names is None:
            # check if file exist (the self.input.event_set_yaml won't exist in a workflow
            # if it is expected to be produced by a method e.g. pluvia_design_event
            # making the workflow fail)
            # TODO think of a better appoach
            if os.path.exists(self.input.event_set_yaml):
                event_set = EventSet.from_yaml(self.input.event_set_yaml)
                for event in event_set.events:
                    future_event_names_list.append(
                        f"{event['name']}_{self.params.scenario_name}_{self.params.future_period}"
                    )
                self.set_expand_wildcard(wildcard, future_event_names_list)
            else:
                raise ValueError(
                    f"{self.input.event_set_yaml} does not exist. Consider providing event_input_names"
                )
        else:
            # Do this as we can directly use pluvial_events.params.event_names as self.params.event_input_names in a workflow
            future_event_names_list.extend(
                [
                    f"{name}_{self.params.scenario_name}_{self.params.future_period}"
                    for name in self.params.event_input_names
                ]
            )

        self.set_expand_wildcard(wildcard, future_event_names_list)

    def run(self):
        """Run the FutureClimateRainfall method."""
        event_set = EventSet.from_yaml(self.input.event_set_yaml)

        if self.params.event_input_names is not None:
            if not [
                event["name"] for event in event_set.events
            ] == self.params.event_input_names:
                raise ValueError(
                    "The event names defined in event_input_names are not in the event_set_yaml."
                )

        # check only if all self.params.event_input_names are in event_set
        # all_events_exist = all(event in event_names_in_set for event in self.params.event_input_names)
        # if not all_events_exist:
        #     raise ValueError("Some events defined in event_input_names are missing in the event_set_yaml.")

        # List to save the scaled events
        future_events_list = []

        for event_set_event in event_set.events:
            # Load the event
            event = Event.from_yaml(event_set_event["path"])
            event_path = event.forcings[0].path

            # Read the event DataFrame and ensure time is parsed as a datetime
            event_df = pd.read_csv(
                event_path,
                index_col=self.params.time_col,
                parse_dates=True,
            )

            # For a historical event pick the year from the first value
            if self.params.design_event_year is None:
                event_year = event_df.index.year[0]
            else:
                # For a design event the representative year is a user defined parameter
                event_year = self.params.design_event_year

            if event_year > self.params.ref_year:
                # Apply linear interpolation to find the temperature change (dT_event_year)
                # for the event year relative to the reference period (e.g., 1981-2010).
                # Interpolation is done between the reference year and the future projection period
                dT_event_year = (
                    self.params.dT / (self.params.future_period - self.params.ref_year)
                ) * (event_year - self.params.ref_year)
            else:
                dT_event_year = 0

            # Apply CC scaling
            scaled_ts = event_df.values * (1 + 0.01 * self.params.alpha) ** (
                self.params.dT - dT_event_year
            )

            # Create a new df to include the time and scaled values
            future_event_df = pd.DataFrame(scaled_ts)
            future_event_df.insert(0, "time", event_df.index)

            filename = (
                f"{event.name}_{self.params.scenario_name}_{self.params.future_period}"
            )

            fmt_dict = {self.params.wildcard: filename}
            forcing_file = Path(str(self.output.future_event_csv).format(**fmt_dict))

            future_event_df.to_csv(forcing_file, index=False)

            future_event_file = Path(
                str(self.output.future_event_yaml).format(**fmt_dict)
            )
            future_event = Event(
                name=filename,
                forcings=[{"type": "rainfall", "path": forcing_file}],
            )
            future_event.set_time_range_from_forcings()
            future_event.to_yaml(future_event_file)
            future_events_list.append({"name": filename, "path": future_event_file})

        # make and save event set yaml file
        future_event_set = EventSet(events=future_events_list)
        future_event_set.to_yaml(self.output.future_event_set_yaml)
