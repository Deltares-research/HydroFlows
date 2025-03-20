"""Future climate sea level method."""

from logging import getLogger
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, model_validator

from hydroflows._typing import FolderPath, ListOfStr, OutPath
from hydroflows.events import Event, EventSet
from hydroflows.utils.units import convert_to_meters
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

logger = getLogger(__name__)

__all__ = ["FutureSLR"]


class Input(Parameters):
    """Input parameters for the :py:class:`FutureSLR` method."""

    event_set_yaml: Path
    """The file path to the event set YAML file, which includes the events to be offset
    for future climate projections, see also :py:class:`hydroflows.events.EventSet`."""


class Output(Parameters):
    """Output parameters for the :py:class:`FutureSLR` method."""

    future_event_yaml: FolderPath
    """The path to the offset event description file,
    see also :py:class:`hydroflows.events.Event`."""

    future_event_csv: Path
    """The path to the offset event csv timeseries file."""

    future_event_set_yaml: Path
    """The path to the offset event set yml file,
    see also :py:class:`hydroflows.events.EventSet`.
    """


class Params(Parameters):
    """Parameters for :py:class:`FutureSLR` method."""

    scenario_name: str
    """Future scenario name for which sea level rise offset is applied."""

    slr_value: float
    """Sea level rise (SLR) change value. This value is added to the input event
    (water level) time series and represents the change in sea level for the specified
    climate scenario.

    Sea level rise change for different periods and emission scenarios
    for different climate models can be taken via:
    `IPCC WGI Interactive Atlas <https://interactive-atlas.ipcc.ch/>`_"""

    slr_unit: Literal["m", "cm", "mm", "ft", "in"] = "m"
    """The unit (length) of the sea level rise value (`slr_value`),
    Valid options are 'm' for meters, 'cm' for centimeters,
    "mm" for milimeters, "ft" for feet and "in" for inches.
    Default is 'm'."""

    event_root: OutPath
    """Root folder to save the derived offset events."""

    wildcard: str = "future_event"
    """The wildcard key for expansion over the offset events."""

    event_names_input: Optional[ListOfStr] = None
    """List of event names to be offset for future climate projections."""

    event_names_output: Optional[ListOfStr] = None
    """List of event names for the offset future climate events."""

    input: Input = Field(exclude=True)
    """Internal variable to link input."""

    @model_validator(mode="after")
    def _validate_model(self):
        # Check if the input event set yaml file exists and check / set event names
        if self.input.event_set_yaml.is_file():
            input_event_set = EventSet.from_yaml(self.input.event_set_yaml)
            event_names = [event["name"] for event in input_event_set.events]
            if self.event_names_input is not None:
                if not set(self.event_names_input).issubset(event_names):
                    not_found = list(set(self.event_names_input) - set(event_names))
                    raise ValueError(
                        f"Events {not_found} event_names_input are missing in the event_set_yaml {self.input.event_set_yaml}."
                    )
            else:
                self.event_names_input = event_names
        # Check if the event_names_output are provided and same length as event_input_name or set them
        if self.event_names_output is not None:
            if len(self.event_names_output) != len(self.event_names_input):
                raise ValueError(
                    "The number of event_names_output should match the number of event_names_input."
                )
        elif self.event_names_input is not None:
            self.event_names_output = [
                f"{name}_{self.scenario_name}" for name in self.event_names_input
            ]
        return self


class FutureSLR(ExpandMethod):
    """Rule for deriving future (climate) sea level (rise) by applying a user-specified offset to an event."""

    name: str = "future_slr"

    _test_kwargs = {
        "scenario_name": "RCP85",
        "slr_value": 0.12,
        "event_set_yaml": Path("event_set.yaml"),
        "event_names_input": ["wl_event1", "wl_event2"],
    }

    def __init__(
        self,
        scenario_name: str,
        slr_value: float,
        event_set_yaml: Path,
        event_root: Path = Path("data/events/future_climate_sea_level"),
        wildcard: str = "future_event",
        event_names_input: Optional[List[str]] = None,
        event_names_output: Optional[List[str]] = None,
        **params,
    ) -> None:
        """Create and validate a FutureSLR instance.

        Parameters
        ----------
        event_set_yaml : Path
            The file path to the event set YAML file, which includes the events to be offset
            for a future climate projection.
        scenario_name: str
            Future scenario name for which the Sea Level Rise offset is applied.
        slr_value: float
            Sea level rise (SLR) change value corresponding to the future climate scenario `scenario_name`.
            This value is added to the input event (water level) time series specified in `event_set_yaml`.
            The unit of the SLR value can be determined in the `slr_unit` parameter. As default the value
            is expected in meters.
        event_root: Path, optional
            Root folder to save the derived scaled events, by default "data/events/future_climate_sea_level".
        wildcard: str
            The wildcard key for expansion over the scaled events, default is "future_event".
        event_names_input, event_names_output: Optional[List[str]]
            List of input event names in event_set_yaml and matching output event names for the scaled events.
            If not provided, event_set_yaml must exist and all events will be scaled.
        **params
            Additional parameters to pass to the FutureSLR Params instance.

        See Also
        --------
        :py:class:`FutureSLR Input <hydroflows.methods.coastal.future_slr.Input>`
        :py:class:`FutureSLR Output <hydroflows.methods.coastal.future_slr.Output>`
        :py:class:`FutureSLR Params <hydroflows.methods.coastal.future_slr.Params>`
        """
        self.input: Input = Input(event_set_yaml=event_set_yaml)

        self.params: Params = Params(
            scenario_name=scenario_name,
            slr_value=slr_value,
            event_root=event_root,
            wildcard=wildcard,
            event_names_input=event_names_input,
            event_names_output=event_names_output,
            input=self.input,  # for validation
            **params,
        )

        wc = "{" + self.params.wildcard + "}"

        self.output: Output = Output(
            future_event_yaml=Path(self.params.event_root) / f"{wc}.yml",
            future_event_csv=Path(self.params.event_root) / f"{wc}.csv",
            future_event_set_yaml=Path(self.params.event_root)
            / f"future_coastal_events_{self.params.scenario_name}.yml",
        )

        self.set_expand_wildcard(wildcard, self.params.event_names_output)

    def _run(self):
        """Run the FutureClimateSLR method."""
        event_set = EventSet.from_yaml(self.input.event_set_yaml)

        # List to save the offset events
        future_events_list = []

        for name, name_out in zip(
            self.params.event_names_input, self.params.event_names_output
        ):
            output = self.get_output_for_wildcards({self.params.wildcard: name_out})

            # Load the event
            event: Event = event_set.get_event(name)
            # get water level forcing
            if len(event.forcings) > 1:
                logger.warning(
                    f"Event {name} has more than one forcing. The first water level forcing is used."
                )
                water_level = [f for f in event.forcings if f["type"] == "water_level"][
                    0
                ]
            else:
                water_level = event.forcings[0]
            event_df = water_level.data.copy()

            # Apply the offset
            future_event_df = event_df + convert_to_meters(
                self.params.slr_value, self.params.slr_unit
            )

            # write forcing timeseries to csv
            future_event_df.to_csv(output["future_event_csv"], index=True)
            # write event to yaml
            water_level.path = output["future_event_csv"]
            future_event = Event(
                name=name_out,
                forcings=[water_level],
            )
            future_event.set_time_range_from_forcings()
            future_event.to_yaml(output["future_event_yaml"])

            # append event to list
            future_events_list.append(
                {"name": name_out, "path": output["future_event_yaml"]}
            )

        # make and save event set yaml file
        future_event_set = EventSet(events=future_events_list)
        future_event_set.to_yaml(self.output.future_event_set_yaml)
