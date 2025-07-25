"""Create hydrographs for coastal waterlevels."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import xarray as xr
from hydromt.stats import eva, get_peak_hydrographs, get_peaks
from hydromt.stats.extremes import plot_return_values
from matplotlib import pyplot as plt
from pydantic import model_validator

from hydroflows._typing import FileDirPath, ListOfInt, ListOfStr, OutputDirPath
from hydroflows.methods.coastal.coastal_utils import plot_hydrographs
from hydroflows.methods.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

logger = logging.getLogger(__name__)


__all__ = ["CoastalDesignEvents", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`CoastalDesignEvents` method."""

    surge_timeseries: Path
    """Path to surge timeseries data."""

    tide_timeseries: Path
    """Path to tides timeseries data."""

    bnd_locations: Path
    """Path to file with locations corresponding to timeseries data."""


class Output(Parameters):
    """Output parameters for the :py:class:`CoastalDesginEvents` method."""

    event_yaml: FileDirPath
    """Path to event description file,
    see also :py:class:`hydroflows.methods.events.Event`."""

    event_csv: Path
    """Path to event timeseries csv file"""

    event_set_yaml: FileDirPath
    """The path to the event set yml file,
    see also :py:class:`hydroflows.methods.events.EventSet`.
    """


class Params(Parameters):
    """Params for the :py:class:`CoastalDesginEvents` method."""

    event_root: OutputDirPath
    """Root folder to save the derived design events."""

    rps: ListOfInt
    """Return periods of interest [year]."""

    event_names: Optional[ListOfStr] = None
    """List of event names for the design events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    ndays: int = 6
    """Duration of derived events in days."""

    t0: datetime = datetime(2020, 1, 1)
    """Arbitrary time of event peak."""

    locs_col_id: str = "stations"
    """Name of locations identifier. Defaults to \"stations\"."""

    plot_fig: bool = True
    """Make hydrograph plots"""

    @model_validator(mode="after")
    def _validate_event_names(self):
        """Use rps to define event names if not provided."""
        if self.event_names is None:
            self.event_names = [f"h_event_rp{rp:03d}" for rp in self.rps]
        elif len(self.event_names) != len(self.rps):
            raise ValueError("event_names should have the same length as rps")
        # create a reference to the event wildcard
        if "event_names" not in self._refs:
            self._refs["event_names"] = f"$wildcards.{self.wildcard}"
        return self


class CoastalDesignEvents(ExpandMethod):
    """Create design events for coastal waterlevels.

    Parameters
    ----------
    surge_timeseries : Path
        Path to surge timeseries data.
    tide_timeseries : Path
        Path to tides timeseries data.
    waterlevel_rps : Path
        Path to the total still waterlevel return values dataset.
    event_root : Path, optional
        Folder root of ouput event catalog file, by default "data/interim/coastal"
    rps : List[float], optional
        Return periods of design events, by default [1, 2, 5, 10, 20, 50, 100].
    event_names : List[str], optional
        List of event names for the design events, by "p_event{i}", where i is the event number.
    wildcard : str, optional
        The wildcard key for expansion over the design events, by default "event".

    See Also
    --------
    :py:class:`CoastalDesignEvents Input <hydroflows.methods.coastal.coastal_design_events.Input>`
    :py:class:`CoastalDesignEvents Output <hydroflows.methods.coastal.coastal_design_events.Output>`
    :py:class:`CoastalDesignEvents Params <hydroflows.methods.coastal.coastal_design_events.Params>`
    """

    name: str = "coastal_design_events"

    _test_kwargs = {
        "surge_timeseries": "surge.nc",
        "tide_timeseries": "tide.nc",
        "bnd_locations": "bnd_locations.gpkg",
    }

    def __init__(
        self,
        surge_timeseries: Path,
        tide_timeseries: Path,
        bnd_locations: Path,
        event_root: Path = Path("data/events/coastal"),
        rps: Optional[List[float]] = None,
        event_names: Optional[List[str]] = None,
        wildcard: str = "event",
        **params,
    ) -> None:
        if rps is None:
            rps = [2, 5, 10, 20, 50, 100]

        self.params: Params = Params(
            event_root=event_root,
            rps=rps,
            event_names=event_names,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(
            surge_timeseries=surge_timeseries,
            tide_timeseries=tide_timeseries,
            bnd_locations=bnd_locations,
        )

        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "coastal_design_events.yml",
        )

        # set wildcards and its expand values
        self.set_expand_wildcard(self.params.wildcard, self.params.event_names)

    def _run(self):
        """Run CoastalDesignEvents method."""
        da_surge = xr.open_dataarray(self.input.surge_timeseries)
        da_tide = xr.open_dataarray(self.input.tide_timeseries)

        locs_col_id = self.params.locs_col_id
        # check if all dims are the same
        if not (da_surge.dims == da_tide.dims):
            raise ValueError("Dimensions of input datasets do not match")
        if locs_col_id not in da_surge.dims or locs_col_id not in da_tide.dims:
            raise ValueError(
                f"Locations identifier {locs_col_id} not found in input data."
            )

        # check the time resolution of the input data and make sure it is the same
        surge_freq = pd.infer_freq(da_surge.time.values)
        tide_freq = pd.infer_freq(da_tide.time.values)
        if surge_freq != tide_freq:
            raise ValueError("Time resolution of input datasets do not match")
        wdw_ndays = pd.Timedelta(f"{self.params.ndays}D")
        wdw_size = int(wdw_ndays / pd.Timedelta(tide_freq))
        min_dist = int(pd.Timedelta("10D") / pd.Timedelta(tide_freq))

        # get mhw tidal hydrographs
        da_mhws_peaks = get_peaks(
            da=da_tide,
            ev_type="BM",
            min_dist=min_dist,
            period="29.5D",
        )
        tide_hydrographs_all = (
            get_peak_hydrographs(
                da_tide,
                da_mhws_peaks,
                wdw_size=wdw_size,
                normalize=False,
            )
            .transpose("time", "peak", ...)
            .load()
        )
        tide_hydrographs_all["time"] = tide_hydrographs_all[
            "time"
        ].values * pd.Timedelta(tide_freq)
        tide_hydrographs = tide_hydrographs_all.median("peak")
        # Singleton dimensions don't survive get_peak_hydrograph function, so reinsert stations dim
        if locs_col_id not in tide_hydrographs.dims:
            tide_hydrographs = tide_hydrographs.expand_dims(dim={locs_col_id: 1})
            tide_hydrographs[locs_col_id] = da_tide[locs_col_id]

        # get normalized surge hydrographs
        surge_peaks = get_peaks(
            da=da_surge,
            ev_type="BM",
            min_dist=min_dist,
            period="year",
        )
        surge_hydrographs_all = (
            get_peak_hydrographs(
                da_surge,
                surge_peaks,
                wdw_size=wdw_size,
                normalize=True,
            )
            .transpose("time", "peak", ...)
            .load()
        )
        surge_hydrographs_all["time"] = surge_hydrographs_all[
            "time"
        ].values * pd.Timedelta(tide_freq)
        surge_hydrographs = surge_hydrographs_all.median("peak")
        # Singleton dimensions don't survive get_peak_hydrograph function, so reinsert stations dim
        if locs_col_id not in surge_hydrographs.dims:
            surge_hydrographs_all = surge_hydrographs_all.expand_dims(
                dim={locs_col_id: 1}
            )
            surge_hydrographs_all[locs_col_id] = da_surge[locs_col_id]
            surge_hydrographs = surge_hydrographs.expand_dims(dim={locs_col_id: 1})
            surge_hydrographs[locs_col_id] = da_surge[locs_col_id]

        # calculate the total water level return values
        da_wl = da_surge + da_tide
        da_wl_eva = eva(
            da_wl, ev_type="BM", min_dist=min_dist, rps=np.array(self.params.rps)
        ).load()
        # if rp contains one value expand the return_values dim with the rp
        if len(self.params.rps) == 1:
            da_wl_eva = da_wl_eva.assign_coords(rps=self.params.rps)
            return_values_expanded = da_wl_eva.return_values.expand_dims(
                rps=da_wl_eva.rps.values
            )
            da_wl_eva = da_wl_eva.assign(return_values=return_values_expanded)

        # construct design hydrographs based on the return values, normalized surge hydrographs and tidal hydrographs
        nontidal_rp = da_wl_eva["return_values"].reset_coords(
            drop=True
        ) - tide_hydrographs.max("time").reset_coords(drop=True)
        h_hydrograph = tide_hydrographs + surge_hydrographs * nontidal_rp
        h_hydrograph = h_hydrograph.assign_coords(
            time=tide_hydrographs["time"].values + pd.to_datetime(self.params.t0)
        )

        root = self.output.event_set_yaml.parent
        events_list = []
        for name, rp in zip(self.params.event_names, self.params.rps):
            output = self.get_output_for_wildcards({self.params.wildcard: name})
            h_hydrograph.sel(rps=rp).transpose().to_pandas().round(2).to_csv(
                output["event_csv"]
            )
            # save event description file
            event = Event(
                name=name,
                forcings=[
                    {
                        "type": "water_level",
                        "path": output["event_csv"],
                        "locs_path": self.input.bnd_locations.resolve(),
                        "locs_id_col": locs_col_id,
                    }
                ],
                probability=1 / rp,
            )
            event.set_time_range_from_forcings()
            event.to_yaml(output["event_yaml"])
            events_list.append({"name": name, "path": output["event_yaml"]})

        event_catalog = EventSet(events=events_list)
        event_catalog.to_yaml(self.output.event_set_yaml)

        if self.params.plot_fig:
            figs_dir = Path(root, "figs")
            figs_dir.mkdir(parents=True, exist_ok=True)

            for station in h_hydrograph[locs_col_id]:
                # plot hydrograph components
                fig, (ax, ax1) = plt.subplots(2, 1, figsize=(8, 10), sharex=True)
                surge_hydrographs_all.sel({locs_col_id: station}).plot.line(
                    ax=ax, x="time", lw=0.3, color="k", alpha=0.5, add_legend=False
                )
                surge_hydrographs.sel({locs_col_id: station}).plot.line(
                    ax=ax, x="time", lw=2, color="k", add_legend=False
                )
                tide_hydrographs.sel({locs_col_id: station}).plot.line(
                    ax=ax1, x="time", lw=2, color="k", add_legend=False
                )
                ax.set_ylabel("Normalized surge signal [-]")
                ax1.set_xlabel("Time")
                ax1.set_ylabel("MHW Tide [m+MSL]")
                ax.set_title("Coastal Waterlevel Hydrograph components")
                ax1.set_title("")
                ax.set_ylim(-0.2, 1.1)
                ax1.set_xlim(
                    tide_hydrographs["time"].min(), tide_hydrographs["time"].max()
                )
                fig.tight_layout()
                fig.savefig(
                    figs_dir / f"hydrograph_components_{station.values}.png",
                    dpi=150,
                    bbox_inches="tight",
                )

                # plot return periods
                try:
                    da_wl_eva_station = da_wl_eva.sel({locs_col_id: station}).squeeze()
                    ax = plot_return_values(
                        da_wl_eva_station["peaks"].reset_coords(drop=True),
                        da_wl_eva_station["parameters"].reset_coords(drop=True),
                        da_wl_eva_station["distribution"].item(),
                        extremes_rate=da_wl_eva_station["extremes_rate"].item(),
                        nsample=100,
                    )
                    ax.set_ylim(
                        da_wl_eva_station["return_values"].values.min() * 0.75,
                        ax.get_ylim()[1],
                    )
                    plt.savefig(
                        figs_dir / f"eva_{station.values}.png",
                        dpi=150,
                        bbox_inches="tight",
                    )
                except Exception as e:
                    # this may fail if too few peaks are found ..
                    logger.warning(
                        f"Could not plot return values for station {station.values}: {e}"
                    )

                # plot design hydrograph
                plot_hydrographs(
                    h_hydrograph.where(
                        h_hydrograph[locs_col_id].isin(station.values), drop=True
                    ).squeeze(),
                    figs_dir / f"hydrographs_stationID_{station.values}.png",
                )
