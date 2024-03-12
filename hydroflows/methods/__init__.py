"""Submodule for hydroflows methods."""

from .fiat import FIATBuild
from .sfincs import SfincsBuild
from .wflow import WflowBuild, WflowUpdateForcing

# registered methods

METHODS = {
    "sfincs_build": SfincsBuild,
    "wflow_build": WflowBuild,
    "fiat_build": FIATBuild,
    "wflow_update_forcing": WflowUpdateForcing,
}
