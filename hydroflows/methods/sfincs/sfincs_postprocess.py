"""Sfincs postprocess method."""

from pathlib import Path

from pydantic import BaseModel, FilePath

from ..method import Method

__all__ = ["SfincsPostprocess"]

class Input(BaseModel):
    """Input parameters."""

    sfincs_inp: FilePath
    sfincs_dep: FilePath


class Output(BaseModel):
    """Output parameters."""

    sfincs_inun: Path


class SfincsPostprocess(Method):
    """Rule for postprocessing Sfincs."""

    name: str = "sfincs_build"
    # params: Params = Params() # optional parameters
    input: Input
    output: Output

    def run(self):
        """Postprocess a SFINCS model run."""
        raise NotImplementedError
