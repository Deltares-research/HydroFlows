"""Submodule for hydroflows methods."""

from .fiat import FIATBuild, FIATRun, FIATUpdateHazard
from .method import Method
from .sfincs import SfincsBuild
from .wflow import WflowBuild, WflowRun, WflowUpdateForcing

# registered methods

METHODS = {
    "sfincs_build": SfincsBuild,
    "wflow_build": WflowBuild,
    "fiat_build": FIATBuild,
    "fiat_run": FIATRun,
    "fiat_update_hazard": FIATUpdateHazard,
    "test_method": Method,  # FIX ME: keep this method private for CLI testing,
    "wflow_run": WflowRun,
    "wflow_update_forcing": WflowUpdateForcing,
}
