"""Submodule for hydroflows methods."""

from .fiat import FIATBuild
from .method import Method
from .sfincs import SfincsBuild
from .wflow import WflowBuild

# registered methods

METHODS = {
    "sfincs_build": SfincsBuild,
    "wflow_build": WflowBuild,
    "fiat_build": FIATBuild,
    "test_method": Method, # FIX ME: keep this method private for CLI testing
}
