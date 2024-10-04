"""Future climate rainfall method."""

import csv
from itertools import product
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
from pydantic import BaseModel, model_validator

from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters


class csv_format(BaseModel):
    """Class to specify the required cols format."""

    period: Literal["2030", "2055", "2085"]
    SSP1: Optional[float] = None
    SSP2: Optional[float] = None
    SSP3: Optional[float] = None

    class Config:
        """Forbid extra fields."""

        extra = "forbid"


class Input(Parameters):
    """Input parameters for the :py:class:`FutureClimateRainfall` method."""

    event_set_yaml: Path
    """The file path to the event set YAML file, which includes the events to be scaled
    for future climate projections, see also :py:class:`hydroflows.events.EventSet`."""

    future_conditions_csv: Path
    """Table containing the change of temperature per scenario and time horizon.
    Temperature anomaly in 2030, 2055 and 2085 (relative to historical baseline)"""

    @model_validator(mode="before")
    def _future_conditions_csv_validator(cls, values):
        # Get the path to the CSV file from values
        future_conditions_csv = values.get("future_conditions_csv")

        # Open the CSV file and validate its contents
        with open(future_conditions_csv) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Validate each row against the `format` class
                csv_format.model_validate(row)

        return values


class Output(Parameters):
    """Output parameters for the :py:class:`FutureClimateRainfall` method."""

    scaled_event_yaml: Path
    """The path to the event description file,
    see also :py:class:`hydroflows.events.Event`."""

    scaled_event_csv: Path
    """The path to the event csv timeseries file"""

    scaled_event_set_yaml: Path
    """The path to the event set yml file,
    see also :py:class:`hydroflows.events.EventSet`.
    """


class Params(Parameters):
    """Parameters for :py:class:`FutureClimateRainfall` method."""

    ref_year: int = 2010
    """Reference historical year for whihc the change of temperature is relative for.
    Used to interpolate to find dT for events after 2010 and before the future
    time horizons, i.e. "2030", "2055", "2085"."""

    alpha: float = 7
    """The rate of change of precipitation with respect to temperature (in % per degree)
    used in Clausius-Clapeyron (CC) scaling"""

    event_root: Path
    """Root folder to save the derived scaled events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the scaled events."""

    # event_names: Optional[ListOfStr] = None
    # """List of event names associated with return periods."""

    # __input_data: Input = PrivateAttr # <-- Private attribute

    # def __init__(self, input_data: Input, **data):
    #     """Ensure `Input` is passed at initialization and cannot be changed."""
    #     super().__init__(**data)
    #     self._input_data = input_data

    # @property
    # def input_data(self):
    #     """Expose a read-only property for accessing the Input instance."""
    #     return self._input_data

    # @model_validator(mode="after")
    # def _model_validator(self):
    #     event_names_list = []
    #     scenario_df = pd.read_csv(self.input_data.future_conditions_csv)
    #     for period, scenario in product(
    #         scenario_df.loc[:, "period"],
    #         scenario_df.columns[scenario_df.columns != 'period']):
    #         event_names_list.append(f"{period}_{scenario}")
    #     if self.event_names is None:
    #         self.event_names = event_names_list
    #     elif len(self.event_names) != len(event_names_list):
    #         raise ValueError("event_names should have the same length as your input")
    #     # create a reference to the event wildcard
    #     if "event_names" not in self._refs:
    #         self._refs["event_names"] = f"$wildcards.{self.wildcard}"


class FutureClimateRainfall(ExpandMethod):
    """Rule for deriving future climate rainfall by scaling an event using Clausius-Clapeyron."""

    name: str = "future_climate_rainfall"

    _test_kwargs = {
        "future_conditions_csv": Path("future_conditions.csv"),
        "event_set_yaml": Path("event_set.yaml"),
    }

    def __init__(
        self,
        future_conditions_csv: Path,
        event_set_yaml: Path,
        event_root: Path = Path("data/events/rainfall"),
        wildcard: str = "scaled_event",
        **params,
    ) -> None:
        """Create and validate a FutureClimateRainfall instance.

        Parameters
        ----------
        event_set_yaml : Path
            The file path to the event set YAML file, which includes the events to be scaled
            for future climate projections.
        future_conditions_csv : Path
            Table containing the change of temperature per scenario and time horizon.
        **params
            Additional parameters to pass to the FutureClimateRainfall Params instance.

        See Also
        --------
        :py:class:`FutureClimateRainfall Input <hydroflows.methods.rainfall.future_climate_rainfall.Input>`
        :py:class:`FutureClimateRainfall Output <hydroflows.methods.rainfall.future_climate_rainfall.Output>`
        :py:class:`FutureClimateRainfall Params <hydroflows.methods.rainfall.future_climate_rainfall.Params>`
        """
        self.params: Params = Params(
            event_root=event_root,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(
            event_set_yaml=event_set_yaml, future_conditions_csv=future_conditions_csv
        )

        wc = "{" + self.params.wildcard + "}"

        self.output: Output = Output(
            scaled_event_yaml=self.params.event_root / f"{wc}.yml",
            scaled_event_csv=self.params.event_root / f"{wc}.csv",
            scaled_event_set_yaml=self.params.event_root / "scaled_pluvial_events.yml",
        )

        scaled_event_names_list = []
        scenario_df = pd.read_csv(self.input.future_conditions_csv)
        event_set = EventSet.from_yaml(self.input.event_set_yaml)
        for event, period, scenario in product(
            event_set.events,
            scenario_df.loc[:, "period"],
            scenario_df.columns[scenario_df.columns != "period"],
        ):
            scaled_event_names_list.append(f"{event['name']}_{period}_{scenario}")

        self.set_expand_wildcard(wildcard, scaled_event_names_list)

    def run(self):
        """Run the FutureClimateRainfall method."""
        scenario_df = pd.read_csv(self.input.future_conditions_csv)
        event_set = EventSet.from_yaml(self.input.event_set_yaml)

        # List to save the scaled events
        scaled_events_list = []

        for event_set_event in event_set.events:
            # Load the event
            event = Event.from_yaml(event_set_event["path"])

            # Read the event DataFrame and ensure time is parsed as a datetime
            event_df = pd.read_csv(
                Path(event.root, f"{event.name}.csv"),
                index_col="time",
                parse_dates=True,
            )

            for _, row in scenario_df.iterrows():
                period = row["period"]

                # Loop through each SSP column
                for ssp in scenario_df.columns[scenario_df.columns != "period"]:
                    # Extract the temperature change (dT) for the specific SSP scenario
                    # relative to the ref period
                    dT = row[ssp]

                    # Get the year of the event
                    event_year = event_df.index.year[0]
                    # Check if the event year is after the reference year
                    if event_year > self.params.ref_year:
                        # Apply linear interpolation to find the temperature change (dT_event_year)
                        # for the event year relative to the reference period (e.g., 1981-2010).
                        # Interpolation is done between the reference year and the future projection period
                        dT_event_year = (dT / (int(period) - self.params.ref_year)) * (
                            event_year - self.params.ref_year
                        )
                    else:
                        dT_event_year = 0

                    # Apply CC scaling
                    scaled_ts = event_df.values * (1 + 0.01 * self.params.alpha) ** (
                        dT - dT_event_year
                    )

                    # Create a new df to include the time and scaled values
                    scaled_event_df = pd.DataFrame(scaled_ts)
                    scaled_event_df.insert(0, "time", event_df.index)

                    filename = f"{event.name}_{int(period)}_{ssp}"
                    fmt_dict = {self.params.wildcard: filename}
                    forcing_file = Path(
                        str(self.output.scaled_event_csv).format(**fmt_dict)
                    )

                    scaled_event_df.to_csv(forcing_file, index=False)

                    scaled_event_file = Path(
                        str(self.output.scaled_event_yaml).format(**fmt_dict)
                    )
                    scaled_event = Event(
                        name=filename,
                        forcings=[{"type": "rainfall", "path": forcing_file}],
                    )
                    scaled_event.set_time_range_from_forcings()
                    scaled_event.to_yaml(scaled_event_file)
                    scaled_events_list.append(
                        {"name": filename, "path": scaled_event_file}
                    )

        # make and save event set yaml file
        scaled_event_set = EventSet(events=scaled_events_list)
        scaled_event_set.to_yaml(self.output.scaled_event_set_yaml)

    # P2 = P1 * (1 + 0.01 * alpha) ** dT
