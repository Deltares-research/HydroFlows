"""Pluvial design events using GPEX global IDF method."""
from pathlib import Path
from typing import List, Literal, Optional

import geopandas as gpd
import xarray as xr
from pydantic import model_validator

from hydroflows._typing import ListOfFloat, ListOfInt, ListOfStr
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["PluvialDesignEventsGPEX"]


class Input(Parameters):
    """Input parameters for :py:class:`PluvialDesignEventsGPEX` method."""

    gpex_nc: Path
    """The file path to the GPEX dataset."""

    region: Path
    """
    The file path to the geometry file for which we want
    to get the GPEX estimates at its centroid.
    An example of such a file could be the SFINCS region GeoJSON.
    """


class Output(Parameters):
    """Output parameters for :py:class:`PluvialDesignEventsGPEX`."""

    event_yaml: Path
    """The path to the event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_csv: Path
    """The path to the event csv timeseries file"""

    event_set_yaml: Path
    """The path to the event set yml file,
    see also :py:class:`hydroflows.events.EventSet`.
    """

class Params(Parameters):
    """Parameters for :py:class:`PluvialDesignEventsGPEX` method."""

    event_root: Path
    """Root folder to save the derived design events."""
    
    # or simply use the path to the nc directly without
    # a data catalog?
    # data_catalog_path: ListOfStr = ["artifact_data"]
    # """File path to the data catalog, which should contain an entry
    # for the GPEX dataset."""

    # data_catalog_entry: str = "gpex"
    # """Name of the entry in the data catalog (specified by `data_catalog_path`)
    # that corresponds to the GPEX dataset."""

    rps: ListOfFloat
    """Return periods of interest."""

    durations: ListOfInt = [1, 2, 3, 6, 12, 24, 36, 48]
    """Intensity Duration Frequencies provided as multiply of the data time step."""

    eva_method: Literal["gev", "mev", "pot"] = "gev"
    """Extreme value distribution method to get the GPEX estimate. 
    Valid options within the GPEX dataset are "gev" for the Generalized Extreme Value ditribution,
    "mev" for the Metastatistical Extreme Value distribution, and "pot" for the
    Peak-Over-Threshold distribution."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    # Note: set by model_validator based on rps if not provided
    event_names: Optional[ListOfStr] = None
    """List of event names associated with return periods."""

    @model_validator(mode="after")
    def _validate_model(self):
        # validate rps
        gpex_available_rps = [2, 5, 10, 20, 39, 50, 100, 200, 500, 1000]
        invalid_values = [v for v in self.rps if v not in gpex_available_rps]
        if invalid_values:
            raise ValueError(
                f"The provided return periods {invalid_values} are not in the predefined list "
                f"of the available GPEX return periods: {gpex_available_rps}."
            )
        # validate event_names
        if self.event_names is None:
            self.event_names = [f"p_event{int(i+1):02d}" for i in range(len(self.rps))]
        elif len(self.event_names) != len(self.rps):
            raise ValueError("event_names should have the same length as rps")
        # create a reference to the event wildcard
        if "event_names" not in self._refs:
            self._refs["event_names"] = f"$wildcards.{self.wildcard}"


class PluvialDesignEventsGPEX(ExpandMethod):
    """Rule for generating pluvial design events based on the GPEX global IDF dataset."""

    name: str = "pluvial_design_events_GPEX"

    _test_kwargs = {
        "region": Path("region.geojson"),
    }

    def __init__(
        self,
        region: Path,
        event_root: Path = Path("data/events/rainfall"),
        rps: Optional[ListOfFloat] = None,
        event_names: Optional[List[str]] = None,
        wildcard: str = "event",
        **params,
    ) -> None:
        """Create and validate a PluvialDesignEventsGPEX instance.

        Parameters
        ----------
        **params
            Additional parameters to pass to the PluvialDesignEventsGPEX Params instance.

        See Also
        --------
        :py:class:`PluvialDesignEventsGPEX Input <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Input>`
        :py:class:`PluvialDesignEventsGPEX Output <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Output>`
        :py:class:`PluvialDesignEventsGPEX Params <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Params>`
        """
        if rps is None:
            rps = [1, 2, 5, 10, 20, 50, 100]
        self.params: Params = Params(
            event_root=event_root,
            rps=rps,
            event_names=event_names,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(region=region)
        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "pluvial_events.yml",
        )
        # set wildcards and its expand values
        self.set_expand_wildcard(wildcard, self.params.event_names)

    def run(self):
        """Run the PluvialDesignEventsGPEX method."""
        # read the region polygon file
        gdf: gpd.GeoDataFrame = gpd.read_file(self.input.region).to_crs("EPSG:4326")
        # calculate the centroid of the polygon
        centroid = gdf.geometry.centroid
        # read the GPEX nc file
        ds = xr.open_dataset(self.input.gpex_nc)[f"{self.params.eva_method}_estimate"]
        # get GPEX data for the pixel closest to the centroid
        ds = ds.sel(
            lat=centroid.y.values[0],
            lon=centroid.x.values[0],
            method="nearest",
        )
        
        