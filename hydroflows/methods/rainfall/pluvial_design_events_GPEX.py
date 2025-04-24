"""Method for generating pluvial design events based on the GPEX global IDF dataset."""

from pathlib import Path
from typing import Literal

import geopandas as gpd
import hydromt  # we need hydromt for raster functionality # noqa: F401
import numpy as np
import pandas as pd
import xarray as xr
from pydantic import model_validator

from hydroflows._typing import FileDirPath, ListOfInt, ListOfStr, OutputDirPath
from hydroflows.methods.events import Event, EventSet
from hydroflows.methods.rainfall.pluvial_design_events import (
    _plot_hyetograph,
    _plot_idf_curves,
    get_hyetograph,
)
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["PluvialDesignEventsGPEX", "Input", "Output", "Params"]

# TODO: move GPEX to data catalog and generalize to use any IDF dataset

GPEX_RPS = [2, 5, 10, 20, 39, 50, 100]  # subset from the GPEX data up to 100yr rp


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

    event_yaml: FileDirPath
    """The path to the event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_csv: Path
    """The path to the event csv timeseries file"""

    event_set_yaml: FileDirPath
    """The path to the event set yml file,
    see also :py:class:`hydroflows.events.EventSet`.
    """


class Params(Parameters):
    """Parameters for :py:class:`PluvialDesignEventsGPEX` method."""

    event_root: OutputDirPath
    """Root folder to save the derived design events."""

    rps: ListOfInt
    """Return periods of interest."""

    duration: int = 48
    """Duration of the produced design event."""

    eva_method: Literal["gev", "gumbel", "mev", "pot"] = "gev"
    """Extreme value distribution method to get the GPEX estimate.
    Valid options within the GPEX dataset are "gev" for the Generalized Extreme Value ditribution,
    "mev" for the Metastatistical Extreme Value distribution, and "pot" for the
    Peak-Over-Threshold distribution."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    # Note: set by model_validator based on rps if not provided
    event_names: ListOfStr | None = None
    """List of event names associated with return periods."""

    t0: str = "2020-01-01"
    """Random initial date for the design events."""

    plot_fig: bool = True
    """Determines whether to plot figures, including the derived design hyetographs
    as well as the calculated IDF curves per return period."""

    save_idf_csv: bool = True
    """Determines whether to save the calculated IDF curve values
    per return period in a csv format."""

    @model_validator(mode="after")
    def _validate_model(self):
        # validate rps
        gpex_available_rps = [2, 5, 10, 20, 39, 50, 100, 200, 500, 1000]
        invalid_values_rps = [v for v in self.rps if v not in gpex_available_rps]
        if invalid_values_rps:
            raise ValueError(
                f"The provided return periods {invalid_values_rps} are not in the predefined list "
                f"of the available GPEX return periods: {gpex_available_rps}."
            )
        gpex_available_durations = [3, 6, 12, 24, 48, 72, 120, 240]
        if self.duration not in gpex_available_durations:
            raise ValueError(
                f"The provided duration {self.duration} is not in the predefined list "
                f"of the available GPEX durations: {gpex_available_durations}."
            )
        # validate event_names
        if self.event_names is None:
            self.event_names = [f"p_event_rp{rp:03d}" for rp in self.rps]
        elif len(self.event_names) != len(self.rps):
            raise ValueError("event_names should have the same length as rps")
        # create a reference to the event wildcard
        if "event_names" not in self._refs:
            self._refs["event_names"] = f"$wildcards.{self.wildcard}"
        return self


class PluvialDesignEventsGPEX(ExpandMethod):
    """Method for generating pluvial design events based on the GPEX global IDF dataset using the alternating block method.

    Parameters
    ----------
    gpex_nc : Path
        The file path to the GPEX data set.
    region : Path
        The file path to the geometry file for which we want
        to derive GPEX estimates at its centroid pixel.
    event_root : Path, optional
        The root folder to save the derived design events, by default "data/events/rainfall".
    rps : List[float], optional
        Return periods of design events, by default [2, 5, 10, 20, 39, 50, 100].
    duration : int
        Duration of the produced design event, by default 48 hours.
    event_names : List[str], optional
        List of event names for the design events, by "p_event{i}", where i is the event number.
    wildcard : str, optional
        The wildcard key for expansion over the design events, by default "event".
    **params
        Additional parameters to pass to the PluvialDesignEventsGPEX Params instance.

    See Also
    --------
    :py:class:`PluvialDesignEventsGPEX Input <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Input>`
    :py:class:`PluvialDesignEventsGPEX Output <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Output>`
    :py:class:`PluvialDesignEventsGPEX Params <hydroflows.methods.rainfall.pluvial_design_events_GPEX.Params>`
    """

    name: str = "pluvial_design_events_GPEX"

    _test_kwargs = {
        "region": Path("region.geojson"),
        "gpex_nc": Path("gpex.nc"),
    }

    def __init__(
        self,
        gpex_nc: Path,
        region: Path,
        event_root: Path = Path("data/events/rainfall"),
        rps: list[int] | None = None,
        duration: int = 48,
        event_names: list[str] | None = None,
        wildcard: str = "event",
        **params,
    ) -> None:
        if rps is None:
            rps = GPEX_RPS
        self.params: Params = Params(
            event_root=event_root,
            rps=rps,
            duration=duration,
            event_names=event_names,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(gpex_nc=gpex_nc, region=region)
        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "pluvial_design_events_GPEX.yml",
        )
        # set wildcards and its expand values
        self.set_expand_wildcard(wildcard, self.params.event_names)

    def _run(self):
        """Run the PluvialDesignEventsGPEX method."""
        # read the region polygon file
        gdf: gpd.GeoDataFrame = gpd.read_file(self.input.region)
        # calculate the centroid of the polygon
        centroid = gdf.geometry.centroid.to_crs("EPSG:4326")
        # read the GPEX nc file
        ds = xr.open_dataset(self.input.gpex_nc)[f"{self.params.eva_method}_estimate"]
        # get the coordinates for the pixel with values closest to the centroid
        gpex2d = ds.isel(tr=0, dur=0).squeeze()
        gpex2d.raster.set_crs(4326)
        gpex2d = gpex2d.raster.clip_bbox(gdf.total_bounds, buffer=1, crs=gdf.crs)
        gpex_cell_centroids = gpex2d.raster.vector_grid("point")
        gpex_cell_centroids["data"] = gpex2d.values.flatten()
        gpex_cell_centroids = gpex_cell_centroids[
            ~np.isnan(gpex_cell_centroids["data"])
        ]
        idx_nearest = gpex_cell_centroids.sindex.nearest(centroid, return_all=False)[1]

        # get GPEX data for the pixel closest to the centroid
        ds_closest = ds.sel(
            lat=gpex_cell_centroids.iloc[idx_nearest].geometry.y.values[0],
            lon=gpex_cell_centroids.iloc[idx_nearest].geometry.x.values[0],
            method="nearest",
            tr=self.params.rps,
        )

        expanded_dur = ds_closest["dur"].values[:, None]
        rates = ds_closest.values / expanded_dur  # estimate rainfall rates

        # Create a new DataArray with the rainfall rates per idf
        da_idf = xr.DataArray(
            rates,
            coords=ds_closest.coords,
            dims=ds_closest.dims,
            attrs=ds_closest.attrs,
        )

        # keep durations up to the max user defined duration
        da_idf = da_idf.sel(dur=slice(None, self.params.duration))

        if self.params.save_idf_csv:
            df_idf = da_idf.rename(
                {"tr": "Return period\n[year]", "dur": "duration"}
            ).to_pandas()
            df_idf.to_csv(Path(self.output.event_csv.parent, "idf.csv"), index=True)

        # Get design events hyetograph for each return period
        p_hyetograph: xr.DataArray = get_hyetograph(da_idf, intensity_dim="dur")

        # make sure there are no negative values
        p_hyetograph = xr.where(p_hyetograph < 0, 0, p_hyetograph)

        root = self.output.event_set_yaml.parent

        # save plots
        if self.params.plot_fig:
            # create a folder to save the figs
            plot_dir = Path(root, "figs")
            plot_dir.mkdir(exist_ok=True)

            _plot_hyetograph(
                p_hyetograph,
                Path(plot_dir, "gpex_rainfall_hyetographs.png"),
                rp_dim="tr",
            )
            _plot_idf_curves(
                da_idf, Path(plot_dir, "gpex_rainfall_idf_curves.png"), rp_dim="tr"
            )

        # random starting time
        dt0 = pd.to_datetime(self.params.t0)
        time_delta = pd.to_timedelta(p_hyetograph["time"], unit="h").round("10min")
        p_hyetograph["time"] = dt0 + time_delta
        p_hyetograph = p_hyetograph.reset_coords(drop=True)

        events_list = []
        for name, rp in zip(self.params.event_names, p_hyetograph["tr"].values):
            output = self.get_output_for_wildcards({self.params.wildcard: name})
            # save p_rp as csv files
            p_hyetograph.sel(tr=rp).to_pandas().round(2).to_csv(output["event_csv"])
            # save event description yaml file
            event = Event(
                name=name,
                forcings=[{"type": "rainfall", "path": output["event_csv"]}],
                return_period=rp,
            )
            event.set_time_range_from_forcings()
            event.to_yaml(output["event_yaml"])
            events_list.append({"name": name, "path": output["event_yaml"]})

        # make and save event set yaml file
        event_set = EventSet(events=events_list)
        event_set.to_yaml(self.output.event_set_yaml)
