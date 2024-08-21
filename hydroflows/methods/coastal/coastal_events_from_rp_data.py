"""Create coastal design events from tide,surge timeseries and return period dataset."""

from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import xarray as xr
from hydromt.stats import get_peak_hydrographs, get_peaks

from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters
from hydroflows.workflow.reference import Ref


class Input(Parameters):
    """Input parameters for the :py:class:`CoastalDesignEvents` method."""

    surge_timeseries: Path
    """Path to surge timeseries data."""

    tide_timeseries: Path
    """Path to tides timeseries data."""

    rp_dataset: Path
    """Path to return period data set"""


class Output(Parameters):
    """Output parameters for the :py:class:`CoastalDesginEvents` method."""

    event_yaml: Path
    """Path to event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_csv: Path
    """Path to event timeseries csv file"""

    event_set_yaml: Path
    """The path to the event set yml file,
    see also :py:class:`hydroflows.events.EventSet`.
    """


class Params(Parameters):
    """Params for the :py:class:`CoastalDesginEvents` method."""

    event_root: Path
    """Root folder to save the derived design events."""

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


class CoastalEventFromRPData(ExpandMethod):
    """Method for deriving extreme event waterlevels from tide and surge timeseries using a return period dataset.

    Utilizes :py:class:`Input <hydroflows.methods.coastal.coastal_events_from_rp_data.Input>`,
    :py:class:`Output <hydroflows.methods.coastal.coastal_events_from_rp_data.Output>`, and
    :py:class:`Params <hydroflows.methods.coastal.coastal_events_from_rp_data.Params>` for method inputs, outputs and params.

    See Also
    --------
    :py:function:`hydroflows.methods.coastal.coastal_events_from_rp_data.plot_hydrographs`
    """

    name: str = "coastal_events_rp_data"

    def __init__(
        self,
        surge_timeseries: Path,
        tide_timeseries: Path,
        rp_dataset: Path,
        event_root: Path = Path("data/events/coastal"),
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
        rp_dataset : Path
            Path to return period dataset.
        waterlevel_rps : Path
            Path to the total still waterlevel return values dataset.
        event_root : Path, optional
            Folder root of ouput event catalog file, by default "data/interim/coastal"
        event_names : List[str], optional
            List of event names for the design events, by "p_event{i}", where i is the event number.
        wildcard : str, optional
            The wildcard key for expansion over the design events, by default "event".

        See Also
        --------
        :py:class:`Input <hydroflows.methods.coastal.coastal_events_from_rp_data.Input>`
        :py:class:`Input <hydroflows.methods.coastal.coastal_events_from_rp_data.Output>`
        :py:class:`Input <hydroflows.methods.coastal.coastal_events_from_rp_data.Params>`
        """
        self.input: Input = Input(
            surge_timeseries=surge_timeseries,
            tide_timeseries=tide_timeseries,
            rp_dataset=rp_dataset,
        )

        rp_data = xr.open_dataset(self.input.rp_dataset)
        rps = rp_data["rps"].values

        if event_names is None:
            event_names = Ref(
                ref=f"$wildcards.{wildcard}",
                value=[f"h_event{int(i+1):02d}" for i in range(len(rps))],
            )
        elif len(event_names) != len(rps):
            raise ValueError("event_names should have the same length as rps")

        self.params: Params = Params(
            event_root=event_root,
            event_names=event_names,
            wildcard=wildcard,
            **params,
        )

        wc = "{" + wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "coastal_events.yml",
        )

        # set wildcards and its expand values
        self.set_expand_wildcard(wildcard, self.params.event_names)

    def run(self):
        """Run CoastalEventsFromRPData method."""
        da_surge = xr.open_dataarray(self.input.surge_timeseries)
        da_tide = xr.open_dataarray(self.input.tide_timeseries)
        da_rps = xr.open_dataset(self.input.rp_dataset)

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
        # Singleton dimensions don't survive get_peak_hydrograph function, so reinsert stations dim
        if "stations" not in tide_hydrographs.dims:
            tide_hydrographs = tide_hydrographs.expand_dims(dim={"stations": 1})
            tide_hydrographs["stations"] = da_tide["stations"]

        da_surge_peaks = get_peaks(
            da_surge,
            ev_type="BM",
            min_dist=6 * 24 * 10,
        )
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
        # Singleton dimensions don't survive get_peak_hydrograph function, so reinsert stations dim
        if "stations" not in surge_hydrographs.dims:
            surge_hydrographs = surge_hydrographs.expand_dims(dim={"stations": 1})
            surge_hydrographs["stations"] = da_surge["stations"]

        nontidal_rp = da_rps["return_values"] - tide_hydrographs
        h_hydrograph = tide_hydrographs + surge_hydrographs * nontidal_rp
        h_hydrograph = h_hydrograph.assign_coords(
            time=pd.to_datetime(self.params.t0)
            + pd.to_timedelta(10 * h_hydrograph["time"], unit="min")
        )

        root = self.output.event_set_yaml.parent
        events_list = []
        for name, rp in zip(self.params.event_names, da_rps["rps"].values):
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
