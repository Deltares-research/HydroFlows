"""Hazard catalog method."""

from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel

from ..workflows.events import EventCatalog
from .method import Method

__all__ = ["HazardCatalog"]

class Input(BaseModel):
    """Input parameters."""

    event_catalog: Path  # event catalog with inputs, used to collect metadata
    depth_hazard_maps: ListOfStr  # collections of inundation maps from a hazard model
    velocity_hazard_maps: ListOfStr



class Output(BaseModel):
    """Output parameters."""

    event_catalog: Path


class HazardCatalog(Method):
    """Method for generating a hazard catalog from a list of inundation maps.

    The method reads a data catalog that was used as origin for the workflow,
    augments hazard layers, and writes back to a .yml

    Parameters
    ----------
    input : Input
        Contains an event_catalog (Path), a list of hazard types and a list of equal
        length of a list of hazard file paths that point to the hazard files that belong
        to the events in the event catalog file

    output : Output
        contains only event_catalog (Path), path to the output catalog file (.yml)

    Examples
    --------
    A simple hazard catalog for only two events and two sets of hazard maps (per type)
    can be created as follows:

        ```python
        from hydroflows.methods import HazardCatalog

        # input catalog with only forcing, should contain only two events
        event_catalog = some_path / "event_catalog_with_forcing.yml"
        types = ["depth", "velocity"]
        hazards = [
            ["depth_p_rp050.tif", "depth_p_rp010.tif"],
            ["velocity_p_rp050.tif", "velocity_p_rp010.tif"]
        ]
        event_catalog_out = some_path / "event_catalog_with_hazards.yml"
        input = {
            "event_catalog": event_catalog,
            "types": types,
            "hazards": hazards
        }
        output = {
            "event_catalog": str(event_catalog_out)
        }
        hazard_catalog = HazardCatalog(input=input, output=output)
        ````
    """

    name: str = "hazard_catalog"
    input: Input
    output: Output

    def run(self):
        """Run the hazard catalog generation method."""
        # read the input event catalog
        event_catalog = EventCatalog.from_yaml(self.input.event_catalog)
        # parse the event inun maps (ensuring paths are relative)
        events_list = []
        # loop over each type

        for n, event_input in enumerate(event_catalog.events):
            event = event_input
            event.hazards = [
                {
                    "type": t, "path": self.input.hazards[m][n]
                } for m, t in enumerate(self.input.types)
            ]
            events_list.append(event)
        event_catalog.events = events_list
        event_catalog.to_yaml(self.output.event_catalog)
