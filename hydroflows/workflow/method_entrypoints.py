"""HydroFlows Method entry points."""

from typing import TYPE_CHECKING, ClassVar, Dict, Optional, Union

from importlib_metadata import EntryPoint, entry_points

if TYPE_CHECKING:
    from hydroflows.workflow import Method

__all__ = ["METHODS"]

__eps__ = {
    "fiat_run": "hydroflows.methods.fiat.fiat_run:FIATRun",
    "fiat_build": "hydroflows.methods.fiat.fiat_build:FIATBuild",
    "fiat_update_hazard": "hydroflows.methods.fiat.fiat_update:FIATUpdateHazard",
    "get_ERA5_rainfall": "hydroflows.methods.rainfall.get_ERA5_rainfall:GetERA5Rainfall",
    "pluvial_design_events": "hydroflows.methods.rainfall.pluvial_design_events:PluvialDesignEvents",
    "pluvial_design_events_GPEX": "hydroflows.methods.rainfall.pluvial_design_events_GPEX:PluvialDesignEventsGPEX",
    "future_climate_rainfall": "hydroflows.methods.rainfall.future_climate_rainfall:FutureClimateRainfall",
    "sfincs_region": "hydroflows.methods.sfincs.sfincs_region:SfincsRegion",
    "sfincs_build": "hydroflows.methods.sfincs.sfincs_build:SfincsBuild",
    "sfincs_run": "hydroflows.methods.sfincs.sfincs_run:SfincsRun",
    "sfincs_postprocess": "hydroflows.methods.sfincs.sfincs_postprocess:SfincsPostprocess",
    "sfincs_downscale": "hydroflows.methods.sfincs.sfincs_downscale:SfincsDownscale",
    "sfincs_update_forcing": "hydroflows.methods.sfincs.sfincs_update_forcing:SfincsUpdateForcing",
    "wflow_build": "hydroflows.methods.wflow.wflow_build:WflowBuild",
    "wflow_run": "hydroflows.methods.wflow.wflow_run:WflowRun",
    "wflow_update_forcing": "hydroflows.methods.wflow.wflow_update_forcing:WflowUpdateForcing",
    "coastal_design_events": "hydroflows.methods.coastal.coastal_design_events:CoastalDesignEvents",
    "coastal_design_events_from_rp_data": "hydroflows.methods.coastal.coastal_design_events_from_rp_data:CoastalDesignEventFromRPData",
    "coastal_tidal_analysis": "hydroflows.methods.coastal.coastal_tidal_analysis:CoastalTidalAnalysis",
    "future_slr": "hydroflows.methods.coastal.future_slr:FutureSLR",
    "get_coast_rp": "hydroflows.methods.coastal.get_coast_rp:GetCoastRP",
    "get_gtsm_data": "hydroflows.methods.coastal.get_gtsm_data:GetGTSMData",
    "floodmarks_validation": "hydroflows.methods.hazard_validation.floodmarks:FloodmarksValidation",
    "fluvial_design_events": "hydroflows.methods.discharge.fluvial_design_events:FluvialDesignEvents",
    "script_method": "hydroflows.methods.script.script_method:ScriptMethod",
    "setup_flood_adapt": "hydroflows.methods.flood_adapt.setup_flood_adapt:SetupFloodAdapt",
    "merge_catalogs": "hydroflows.methods.catalog.merge_catalogs:MergeCatalogs",
    "historical_events": "hydroflows.methods.historical_events.historical_events:HistoricalEvents",
}


class MethodEPS:
    """Method entry points.

    The class is used to allow users to contribute methods and
    load local methods lazily. Methods are loaded by name or class name.
    """

    group: ClassVar[str] = "hydroflows.methods"

    def __init__(self, eps: Optional[Dict[str, Union[str, EntryPoint]]] = None) -> None:
        """Initialize."""
        # cache entry points by name property and class.__name__
        self._entry_points: Dict[str, EntryPoint] = {}
        # local eps
        eps = eps or {}
        # load other eps
        eps.update({ep.name: ep for ep in entry_points(group=self.group)})
        # add eps
        for name, ep in eps.items():
            self.set_ep(name, ep)

    @property
    def entry_points(self) -> Dict[str, EntryPoint]:
        """List of method entry points."""
        return self._entry_points

    def set_ep(self, name: str, ep: Union[str, EntryPoint]) -> None:
        name = name.lower()
        if name in self._entry_points:
            raise ValueError(f"Duplicate entry point {name}")
        if isinstance(ep, str):
            ep = EntryPoint(name, ep, self.group)
        elif not isinstance(ep, EntryPoint):
            raise ValueError(f"Invalid entry point {ep}")
        self._entry_points[name] = ep

    def get_ep(self, name: str) -> EntryPoint:
        """Get entry point by name."""
        name = name.lower()
        ep = self.entry_points.get(name)
        if ep is None:  # try by class name
            for ep0 in self.entry_points.values():
                if ep0.value.split(":")[-1].split(".")[-1].lower() == name:
                    ep = ep0
                    break
        if ep is None:
            raise ValueError(f"Method {name} not found")
        return ep

    def load(self, name: str) -> "Method":
        """Load method by name."""
        from hydroflows.workflow import Method

        obj = self.get_ep(name).load()
        if not issubclass(obj, Method):
            raise ValueError(f"Method {name} is not a valid Method")

        return obj


METHODS = MethodEPS(__eps__)
