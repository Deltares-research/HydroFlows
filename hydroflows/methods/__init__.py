"""Submodule for hydroflows methods."""

from .fiat import FIATBuild, FIATRun, FIATUpdateHazard
from .hazard_catalog import HazardCatalog
from .rainfall import GetERA5Rainfall, PluvialDesignEvents
from .sfincs import SfincsBuild, SfincsPostprocess, SfincsRun, SfincsUpdateForcing
from .wflow import WflowBuild, WflowDesignHydro, WflowRun, WflowUpdateForcing

# registered methods

# TODO: turn in to list for entry points, similar to hydromt

METHODS = {
    "sfincs_build": SfincsBuild,
    "wflow_build": WflowBuild,
    "fiat_build": FIATBuild,
    "fiat_run": FIATRun,
    "fiat_update_hazard": FIATUpdateHazard,
    "wflow_run": WflowRun,
    "wflow_update_forcing": WflowUpdateForcing,
    "sfincs_update_forcing": SfincsUpdateForcing,
    "sfincs_run": SfincsRun,
    "sfincs_postprocess": SfincsPostprocess,
    "pluvial_design_events": PluvialDesignEvents,
    "hazard_catalog": HazardCatalog,
    "get_ERA5_rainfall": GetERA5Rainfall,
    "wflow_design_hydro": WflowDesignHydro,
}
