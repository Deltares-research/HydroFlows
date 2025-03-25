"""Derive future (climate) sea level (rise) events by applying a user-specified offset to an event."""

from logging import getLogger
from pathlib import Path
from typing import List, Literal, Optional

from hydroflows._typing import ClimateScenariosDict, ListOfStr
from hydroflows.events import Event, EventSet
from hydroflows.utils.units import convert_to_meters
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

logger = getLogger(__name__)

__all__ = ["FutureSLR", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`FutureSLR` method."""

    event_set_yaml: Path
    """The file path to the event set YAML file, which includes the events to be offset
    for future climate projections, see also :py:class:`hydroflows.events.EventSet`."""


class Output(Parameters):
    """Output parameters for the :py:class:`FutureSLR` method."""

    future_event_yaml: Path
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

    scenarios: ClimateScenariosDict
    """Future scenario name, e.g. "rcp45_2050", and sea level rise.

    The sea level rise value is added to the input event water level time series.

    Sea level rise change for different periods and emission scenarios
    for different climate models can be taken via:
    `IPCC WGI Interactive Atlas <https://interactive-atlas.ipcc.ch/>`_"""

    slr_unit: Literal["m", "cm", "mm", "ft", "in"] = "m"
    """The unit (length) of the sea level rise value (`slr_value`),
    Valid options are 'm' for meters, 'cm' for centimeters,
    "mm" for milimeters, "ft" for feet and "in" for inches.
    Default is 'm'."""

    event_root: Path
    """Root folder to save the derived offset events."""

    event_names: Optional[ListOfStr]
    """List of event names (subset of event_set_yaml events)."""

    event_wildcard: str = "future_event"
    """The wildcard key for expansion over the offset events."""

    scenario_wildcard: str = "scenario"
    """The wildcard key for expansion over the scenarios."""


class FutureSLR(ExpandMethod):
    """Derive future (climate) sea level (rise) events by applying a user-specified offset to an event.

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

    name: str = "future_slr"

    _test_kwargs = {
        "scenarios": {"rcp45_2050": 0.1},
        "event_set_yaml": Path("event_set.yaml"),
        "event_names": ["wl_event1", "wl_event2"],
    }

    def __init__(
        self,
        scenarios: dict[str, float],
        event_set_yaml: Path,
        event_names: Optional[List[str]] = None,
        event_root: Path = Path("data/events/future_climate_sea_level"),
        event_wildcard: str = "future_event",
        scenario_wildcard: str = "scenario",
        **params,
    ) -> None:
        self.input: Input = Input(event_set_yaml=event_set_yaml)

        event_set_names = None
        if self.input.event_set_yaml.exists():
            event_set = EventSet.from_yaml(self.input.event_set_yaml)
            event_set_names = [event["name"] for event in event_set.events]

        if event_names is None and event_set_names is not None:
            event_names = event_set_names
        elif event_names is None:
            raise ValueError(
                "event_names must be provided if event_set_yaml does not exist"
            )

        self.params: Params = Params(
            scenarios=scenarios,
            event_root=event_root,
            event_wildcard=event_wildcard,
            scenario_wildcard=scenario_wildcard,
            event_names=event_names,
            **params,
        )
        if event_set_names is not None:
            # make sure all event names are in the event set
            if not set(event_names).issubset(event_set_names):
                raise ValueError(
                    "event_names must be subset of event names in event_set_yaml"
                )

        ewc = "{" + self.params.event_wildcard + "}"
        swc = "{" + self.params.scenario_wildcard + "}"

        self.output: Output = Output(
            future_event_yaml=self.params.event_root / swc / f"{ewc}.yml",
            future_event_csv=self.params.event_root / swc / f"{ewc}.csv",
            future_event_set_yaml=self.params.event_root
            / swc
            / f"{self.input.event_set_yaml.stem}_{swc}.yml",
        )

        self.set_expand_wildcard(self.params.event_wildcard, self.params.event_names)
        self.set_expand_wildcard(
            self.params.scenario_wildcard, list(self.params.scenarios.keys())
        )

    def _run(self):
        """Run the FutureClimateSLR method."""
        event_set = EventSet.from_yaml(self.input.event_set_yaml)

        # List to save the offset events
        future_events_list = []

        for scenario, slr_value in self.params.scenarios.items():
            # List to save the scaled events
            future_events_list = []

            for name in self.params.event_names:
                output = self.get_output_for_wildcards(
                    {
                        self.params.event_wildcard: name,
                        self.params.scenario_wildcard: scenario,
                    }
                )

                # Load the event
                event: Event = event_set.get_event(name)

                # scale water level forcing, keep other forcings
                forcings = []
                slr_m = convert_to_meters(slr_value, self.params.slr_unit)
                for forcing in event.forcings:
                    if forcing.type == "water_level":
                        # update and write forcing timeseries to csv
                        future_event_df = forcing.data.copy() + slr_m
                        future_event_df.to_csv(output["future_event_csv"], index=True)
                        forcing.path = output["future_event_csv"]
                    forcings.append(forcing)

                # write event to yaml
                future_event = Event(
                    name=name,
                    forcings=forcings,
                    return_period=event.return_period,
                )
                future_event.set_time_range_from_forcings()
                future_event.to_yaml(output["future_event_yaml"])

                # append event to list
                future_events_list.append(
                    {"name": name, "path": output["future_event_yaml"]}
                )

            # make and save event set yaml file
            future_event_set = EventSet(events=future_events_list)
            future_event_set.to_yaml(output["future_event_set_yaml"])
