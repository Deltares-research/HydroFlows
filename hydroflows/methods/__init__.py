"""Submodule for hydroflows methods."""

from .sfincs import SfincsBuild
from .wflow import WflowBuild

# registered methods

METHODS = {
    "sfincs_build": SfincsBuild,
    "wflow_build": WflowBuild,
    # add more methods here
}
