"""Submodule for hydroflows methods."""

# NOTE all methods should be imported here to make them discoverable
# in the Method._get_subclasses() method
from hydroflows.methods.fiat import FIATBuild, FIATRun, FIATUpdateHazard
from hydroflows.methods.rainfall import GetERA5Rainfall, PluvialDesignEvents
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsPostprocess,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.methods.wflow import (
    WflowBuild,
    WflowDesignHydro,
    WflowRun,
    WflowUpdateForcing,
)

__all__ = []
