"""Submodule for hydroflows methods."""

from .fiat import FIATBuild, FIATRun, FIATUpdateHazard
from .method import Method
from .rainfall import GetERA5Rainfall, PluvialDesignEvents
from .sfincs import SfincsBuild, SfincsUpdateForcing
from .wflow import WflowBuild, WflowDesignHydro, WflowRun, WflowUpdateForcing

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
    "sfincs_update_forcing": SfincsUpdateForcing,
    "pluvial_design_events": PluvialDesignEvents,
    "get_ERA5_rainfall": GetERA5Rainfall,
    "wflow_design_hydro": WflowDesignHydro
}
