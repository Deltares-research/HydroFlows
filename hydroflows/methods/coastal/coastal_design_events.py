"""Create hydrographs for coastal waterlevels."""

from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import xarray as xr
from hydromt.stats import get_peak_hydrographs, get_peaks

from hydroflows._typing import ListOfFloat
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters
from hydroflows.workflow.reference import Ref

__all__ = ["CoastalDesignEvents"]


class Input(Parameters):
    """Input parameters for the :py:class:`CoastalDesignEvents` method."""

    surge_timeseries: Path
    """Path to surge timeseries data."""

    tide_timeseries: Path
    """Path to tides timeseries data."""

    waterlevel_rps: Path
    """Path to the total still waterlevel return values dataset."""


class Output(Parameters):
    """Output parameters for the :py:class:`CoastalDesginEvents` method."""

    event_yaml: Path
    """Path to event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_csv: Path
    """Path to event timeseries csv file"""

    # bnd_locations: Path
    # """Path to file containing water level locations"""

    event_set_yaml: Path
    """The path to the event set yml file,
    see also :py:class:`hydroflows.events.EventSet`.
    """


class Params(Parameters):
    """Params for the :py:class:`CoastalDesginEvents` method."""

    event_root: Path
    """Root folder to save the derived design events."""

    rps: ListOfFloat
    """Return periods of interest."""

    event_names: List[str]
    """List of event names for the design events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    ndays: int = 6
    """Duration of derived events in days."""

    t0: str = "2020-01-01"
    """Arbitrary time of event peak."""

    plot_fig: bool = True
    """Make hydrograph plots"""


class CoastalDesignEvents(ExpandMethod):
    """Method for deriving extreme event waterlevels from tide and surge timeseries.

    Utilizes :py:class:`Input <hydroflows.methods.coastal.coastal_design_events.Input>`,
    :py:class:`Output <hydroflows.methods.coastal.coastal_design_events.Output>`, and
    :py:class:`Params <hydroflows.methods.coastal.coastal_design_events.Params>` for method inputs, outputs and params.

    See Also
    --------
    :py:function:`hydroflows.methods.coastal.coastal_design_events.plot_hydrographs`
    """

    name: str = "coastal_design_events"

    def __init__(
        self,
        surge_timeseries: Path,
        tide_timeseries: Path,
        waterlevel_rps: Path,
        event_root: Path = Path("data/events/coastal"),
        rps: Optional[List[float]] = None,
        event_names: Optional[List[str]] = None,
        wildcard: str = "event",
        **params,
    ) -> None:
        """Create and validate CoastalDesignEvents instance.

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
        :py:class:`Input <hydroflows.methods.coastal.coastal_design_events.Input>`
        :py:class:`Input <hydroflows.methods.coastal.coastal_design_events.Output>`
        :py:class:`Input <hydroflows.methods.coastal.coastal_design_events.Params>`
        """
        if rps is None:
            rps = [1, 2, 5, 10, 20, 50, 100]
        if event_names is None:
            event_names = Ref(
                ref=f"$wildcards.{wildcard}",
                value=[f"h_event{int(i+1):02d}" for i in range(len(rps))],
            )
        elif len(event_names) != len(rps):
            raise ValueError("event_names should have the same length as rps")

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
            waterlevel_rps=waterlevel_rps,
        )

        wc = "{" + wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "coastal_events.yml",
            # bnd_locations=self.params.event_root / "coastal_locations.gpkg",
        )

        # set wildcards and its expand values
        self.set_expand_wildcard(wildcard, self.params.event_names)

    def run(self):
        """Run CoastalDesignEvents method."""
        da_surge = xr.open_dataarray(self.input.surge_timeseries)
        da_tide = xr.open_dataarray(self.input.tide_timeseries)
        da_rps = xr.open_dataset(self.input.waterlevel_rps)

        # check if all dims are the same
        if not (da_surge.dims == da_tide.dims):
            raise ValueError("Dimensions of input datasets do not match")
        if "stations" not in da_surge.dims:
            da_surge = da_surge.expand_dims(dim={"stations": 1})
            da_tide = da_tide.expand_dims(dim={"stations": 1})
            da_rps = da_rps.expand_dims(dim={"stations": 1})

        da_mhws_peaks = get_peaks(
            da=da_tide,
            ev_type="BM",
            min_dist=6 * 24 * 10,  # FIXME use da_tide time resolution
            period="29.5D",
        )
        tide_hydrographs = (
            get_peak_hydrographs(
                da_tide,
                da_mhws_peaks,
                wdw_size=int(6 * 24 * self.params.ndays),
                normalize=False,
            )
            .transpose("time", "peak", ...)
            .mean("peak")
        )

        da_surge_peaks = get_peaks(da_surge, "BM", min_dist=6 * 24 * 10)
        surge_hydrographs = (
            get_peak_hydrographs(
                da_surge,
                da_surge_peaks,
                wdw_size=int(6 * 24 * self.params.ndays),
                normalize=False,
            )
            .transpose("time", "peak", ...)
            .mean("peak")
        )

        nontidal_rp = da_rps["return_values"] - tide_hydrographs
        h_hydrograph = tide_hydrographs + surge_hydrographs * nontidal_rp
        h_hydrograph = h_hydrograph.assign_coords(
            time=pd.to_datetime(self.params.t0)
            + pd.to_timedelta(10 * h_hydrograph["time"], unit="min")
        )

        root = self.output.event_set_yaml.parent
        events_list = []
        for name, rp in zip(self.params.event_names, self.params.rps):
            # save event forcing file
            fmt_dict = {self.params.wildcard: name}
            forcing_file = Path(str(self.output.event_csv).format(**fmt_dict))
            h_hydrograph.sel(rps=rp).transpose().to_pandas().round(2).to_csv(
                forcing_file
            )
            # save event description file
            event_file = Path(str(self.output.event_yaml).format(**fmt_dict))
            event = Event(
                name=name,
                forcings=[{"type": "water_level", "path": forcing_file.name}],
                probability=1 / rp,
            )
            event.set_time_range_from_forcings()
            event.to_yaml(event_file)
            events_list.append({"name": name, "path": event_file.name})

        event_catalog = EventSet(events=events_list)
        event_catalog.to_yaml(self.output.event_set_yaml)

        # # TODO: move to get_data ?
        # locs = []
        # for station in h_hydrograph.stations:
        #     locs.append(
        #         Point(
        #             h_hydrograph.sel(stations=station).lon.values,
        #             h_hydrograph.sel(stations=station).lat.values,
        #         )
        #     )

        # locations = gpd.GeoDataFrame(
        #     {"index": h_hydrograph.stations.values, "geometry": locs}, crs=4326
        # )
        # locations.to_file(self.output.bnd_locations, driver="GPKG")

        if self.params.plot_fig:
            figs_dir = Path(root, "figs")
            figs_dir.mkdir(parents=True, exist_ok=True)
            for station in h_hydrograph.stations:
                fig_file = figs_dir / f"hydrographs_stationID_{station.values}.png"
                plot_hydrographs(h_hydrograph.sel(stations=station), fig_file)


def plot_hydrographs(
    da_hydrograph: xr.DataArray,
    savepath: Path,
) -> None:
    """Plot and save hydrographs.

    Parameters
    ----------
    da_hydrograph : xr.DataArray
        DataArray containing hydrographs. Has rps and time dimensions.
    savepath : Path
        Save path for figure.
    """
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot()

    da_hydrograph.rename({"rps": "Return Period [year]"}).plot.line(ax=ax, x="time")
    ax.set_xlabel("Time")
    ax.set_ylabel("Waterlevel [m+MSL]")
    ax.set_title("Coastal Waterlevel Hydrographs")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(savepath, dpi=150, bbox_inches="tight")
