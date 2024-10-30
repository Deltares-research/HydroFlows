"""Pluvial design events using GPEX global IDF method."""

from pathlib import Path
from typing import List, Optional

from hydroflows._typing import ListOfFloat, ListOfStr
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["PluvialDesignEventsGPEX"]


class Input(Parameters):
    """Input parameters for :py:class:`PluvialDesignEventsGPEX` method."""

    region: Path
    """
    The file path to the geometry file for which we want
    to get the GPEX estimates at its centroid.
    An example of such a file could be the SFINCS region GeoJSON.
    """


class Output(Parameters):
    """Output parameters for :py:class:`PluvialDesignEventsGPEX`."""

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
    """Parameters for :py:class:`PluvialDesignEventsGPEX` method."""

    event_root: Path
    """Root folder to save the derived design events."""

    rps: ListOfFloat
    """Return periods of interest."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    # Note: set by model_validator based on rps if not provided
    event_names: Optional[ListOfStr] = None
    """List of event names associated with return periods."""


class PluvialDesignEventsGPEX(ExpandMethod):
    """Rule for generating pluvial design events based on the GPEX global IDF dataset."""

    name: str = "pluvial_design_events_GPEX"

    _test_kwargs = {
        "region": Path("region.geojson"),
    }

    def __init__(
        self,
        region: Path,
        event_root: Path = Path("data/events/rainfall"),
        rps: Optional[ListOfFloat] = None,
        event_names: Optional[List[str]] = None,
        wildcard: str = "event",
        **params,
    ) -> None:
        """Create and validate a PluvialDesignEventsGPEX instance.

        Parameters
        ----------
        **params
            Additional parameters to pass to the PluvialDesignEventsGPEX Params instance.

        See Also
        --------
        :py:class:`PluvialDesignEventsGPEX Input <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Input>`
        :py:class:`PluvialDesignEventsGPEX Output <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Output>`
        :py:class:`PluvialDesignEventsGPEX Params <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Params>`
        """
        if rps is None:
            rps = [1, 2, 5, 10, 20, 50, 100]
        self.params: Params = Params(
            event_root=event_root,
            rps=rps,
            event_names=event_names,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(region=region)
        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "pluvial_events.yml",
        )
        # set wildcards and its expand values
        self.set_expand_wildcard(wildcard, self.params.event_names)

        def run(self):
        """Run the PluvialDesignEventsGPEX method."""
        