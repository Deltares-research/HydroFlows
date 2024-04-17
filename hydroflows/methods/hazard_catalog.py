"""Hazard catalog method."""

from pathlib import Path
from typing import List

from pydantic import BaseModel, FilePath

from .method import Method

__all__ = ["HazardCatalog"]

class Input(BaseModel):
    """Input parameters."""

    event_catalog: Path  # event catalog with inputs, used to collect metadata
    inun_fns: List[FilePath]  # a collection of inundation maps from a hazard model


class Output(BaseModel):
    """Output parameters."""

    event_catalog: Path


class HazardCatalog(Method):
    """Method for generating a hazard catalog from a list of inundation maps."""

    name: str = "hazard_catalog"
    input: Input
    output: Output

    def run(self):
        """Run the hazard catalog generation method."""
        # read the input event catalog
        events_input = {}

        # parse the event inun maps (ensuring paths are relative)
        events_list = []
        for event_input, fn_inun in zip(events_input, self.input.inun_fns):
            event = event_input
            event["inundation"]: fn_inun
        events_list.append(event)

        # make a data catalog
