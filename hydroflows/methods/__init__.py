"""Submodule for hydroflows methods."""

from .sfincs import SfincsBuild

# registered methods

METHODS = {
    "sfincs_build": SfincsBuild,
    # add more methods here
}
