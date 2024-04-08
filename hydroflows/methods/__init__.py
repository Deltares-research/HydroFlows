"""Submodule for hydroflows methods."""

from .fiat import FIATBuild
from .method import Method
from .rainfall import PluvialDesignHyeto
from .sfincs import SfincsBuild, SfincsUpdateForcing
from .wflow import WflowBuild, WflowRun, WflowUpdateForcing

# registered methods

METHODS = {
    "sfincs_build": SfincsBuild,
    "wflow_build": WflowBuild,
    "fiat_build": FIATBuild,
    "test_method": Method,  # FIX ME: keep this method private for CLI testing,
    "wflow_run": WflowRun,
    "wflow_update_forcing": WflowUpdateForcing,
    "sfincs_update_forcing": SfincsUpdateForcing,
    "pluvial_design_hyeto": PluvialDesignHyeto,
}
