"""Wflow design hydrograph method."""
from pathlib import Path

import xarray as xr
from pydantic import BaseModel, FilePath

from ..method import Method

__all__ = ["WflowDesignHydro"]

class Input(BaseModel):
    """Input parameters."""

    time_series_fn: FilePath

class Output(BaseModel):
    """Output parameters."""

    design_hydrograph: Path

class Params(BaseModel):
    """Parameters."""

    ev_type: str

class WflowDesignHydro(Method):
    """Rule for creating fluvial design hydrograph."""

    name: str = "wflow_design_hydro"
    params: Params = Params() # optional parameters
    input: Input
    output: Output

    def run(self):
        """Run the Wflow design hydrograph method."""
        #read the provided wflow time series
        xr.open_dataset(self.input.time_series_fn)
