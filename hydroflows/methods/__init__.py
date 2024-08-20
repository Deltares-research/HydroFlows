"""Submodule for hydroflows methods."""

# NOTE all methods should be imported here to make them discoverable
# in the Method._get_subclasses() method
from .coastal import (
    CoastalDesignEvents,
    GetCoastRP,
    GetGTSMData,
    GetWaterlevelRPS,
    TideSurgeTimeseries,
)
from .fiat import FIATBuild, FIATRun, FIATUpdateHazard
from .rainfall import GetERA5Rainfall, PluvialDesignEvents
from .sfincs import SfincsBuild, SfincsPostprocess, SfincsRun, SfincsUpdateForcing
from .wflow import WflowBuild, WflowDesignHydro, WflowRun, WflowUpdateForcing

__all__ = []
