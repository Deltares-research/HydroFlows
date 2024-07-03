"""Hazard set method."""
import os.path
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from hydroflows._typing import ListOfStr
from hydroflows.events import EventSet, Hazard
from hydroflows.methods.method import Method

__all__ = ["HazardSet"]


class Input(BaseModel):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`HazardSet` method.
    """

    event_set: Path
    """The path to the event set with inputs, used to collect metadata."""

    depth_hazard_maps: ListOfStr
    """Collections of inundation maps from a hazard model."""

    velocity_hazard_maps: Optional[ListOfStr] = None
    """Velocity hazard maps, e.g. types: List[Literal["depth", "velocity"]]."""


class Output(BaseModel):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`HazardSet` method.
    """

    event_set: Path
    """The path to the output event set file (.yml)."""


class HazardSet(Method):
    """Rule for generating a hazard set from a list of inundation maps.

    This class utilizes the :py:class:`Input <hydroflows.methods.hazard_set.Input>` and
    :py:class:`Output <hydroflows.methods.hazard_set.Output>` classes to read a event set,
    augment hazard layers, and write the updated set back to a .yml file.

    Examples
    --------
    A simple hazard set for only two events and two sets of hazard maps (per type)
    can be created as follows::

        from hydroflows.methods import HazardSet

        # input set with only forcing, should contain only two events
        event_set = some_path / "event_set_with_forcing.yml"
        depth_hazard_maps = ["depth_p_rp050.tif", "depth_p_rp010.tif"]
        velocity_hazard_maps = ["velocity_p_rp050.tif", "velocity_p_rp010.tif"]
        event_set_out = some_path / "event_set_with_hazards.yml"
        input = {
            "event_set": event_set,
            "types": types,
            "hazard_maps": hazard_maps
        }
        output = {
            "event_set": str(event_set_out)
        }
        hazard_set = HazardSet(input=input, output=output)
    """

    name: str = "hazard_set"

    input: Input
    """Contains an event_set (Path), a list of hazard maps for depth and (if
    needed) velocity maps."""

    output: Output
    """Contains only event_set (Path), path to the output event set file (.yml)."""

    def run(self):
        """Run the hazard set generation method."""
        # read the input event set
        event_set = EventSet.from_yaml(self.input.event_set)
        # alter roots_hazard to actual path assuming all maps are in the same folder
        event_set.roots.root_hazards = Path(os.curdir)
        # parse the event inun maps (ensuring paths are relative)
        events_list = []
        # loop over each type
        for n, event_input in enumerate(event_set.events):
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
        event_set.events = events_list
        event_set.to_yaml(self.output.event_set)
