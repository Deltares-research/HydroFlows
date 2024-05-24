"""Hazard catalog method."""
import os.path
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from .._typing import ListOfStr
from ..workflows.events import EventCatalog, Hazard
from .method import Method

__all__ = ["HazardCatalog"]


class Input(BaseModel):
    """Input parameters."""

    event_catalog: Path  # event catalog with inputs, used to collect metadata
    depth_hazard_maps: ListOfStr  # collections of inundation maps from a hazard model
    velocity_hazard_maps: Optional[ListOfStr] = None
    # types: List[Literal["depth", "velocity"]] = None


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
        Contains an event_catalog (Path), a list of hazard maps for depth and (if
        needed) velocity maps.

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
        depth_hazard_maps = ["depth_p_rp050.tif", "depth_p_rp010.tif"]
        velocity_hazard_maps = ["velocity_p_rp050.tif", "velocity_p_rp010.tif"]
        event_catalog_out = some_path / "event_catalog_with_hazards.yml"
        input = {
            "event_catalog": event_catalog,
            "types": types,
            "hazard_maps": hazard_maps
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
        # alter roots_hazard to actual path assuming all maps are in the same folder
        event_catalog.roots.root_hazards = Path(os.curdir)
        # parse the event inun maps (ensuring paths are relative)
        events_list = []
        # loop over each type
        for n, event_input in enumerate(event_catalog.events):
            event = event_input
            event.hazards = [
                Hazard(
                    **{
                        "type": "depth",
                        "path": os.path.relpath(
                            self.input.depth_hazard_maps[n], os.curdir
                        ),
                    }
                )
            ]
            if self.input.velocity_hazard_maps:
                event.hazards.append(
                    Hazard(
                        **{
                            "type": "velocity",
                            "path": os.path.relpath(
                                self.input.velocity_hazard_maps[n], os.curdir
                            ),
                        }
                    )
                )
            events_list.append(event)
        event_catalog.events = events_list
        event_catalog.to_yaml(self.output.event_catalog)
