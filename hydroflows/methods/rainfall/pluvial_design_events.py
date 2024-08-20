"""Pluvial design events method."""

from pathlib import Path
from typing import List, Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from hydroflows._typing import ListOfFloat, ListOfInt
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters
from hydroflows.workflow.reference import Ref

__all__ = ["PluvialDesignEvents"]


class Input(Parameters):
    """Input parameters for :py:class:`PluvialDesignEvents` method."""

    precip_nc: Path
    """
    The file path to the rainfall time series in NetCDF format which are used
    to apply EVA and derive design events. This file should contain a time dimension
    This time series can be derived either by the
    :py:class:`hydroflows.methods.rainfall.get_ERA5_rainfall.GetERA5Rainfall`
    or can be directly supplied by the user.
    """


class Output(Parameters):
    """Output parameters for :py:class:`PluvialDesignEvents`."""

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
    """Parameters for :py:class:`PluvialDesignEvents` method."""

    event_root: Path
    """Root folder to save the derived design events."""

    rps: ListOfFloat
    """Return periods of interest."""

    event_names: List[str]
    """List of event names associated with return periods."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    durations: ListOfInt = [1, 2, 3, 6, 12, 24, 36, 48]
    """Intensity Duration Frequencies provided as multiply of the data time step."""

    min_dist_days: int = 0
    """Minimum distance between events/peaks measured in days."""

    ev_type: Literal["BM", "POT"] = "BM"
    """Method to select events/peaks. Valid options are 'BM' for block maxima or 'POT' for Peak over threshold."""

    qthresh: float = 0.95
    """Quantile threshold used with peaks over threshold method."""

    min_sample_perc: int = 80
    """Minimum sample percentage in a valid block. Peaks of invalid bins are set to NaN."""

    time_dim: str = "time"
    """Time dimension of the input time series provided in :py:class:`Input` class."""

    t0: str = "2020-01-01"
    """Random initial date for the design events."""

    plot_fig: bool = True
    """Determines whether to plot figures, including the derived design hyetographs
    as well as the calculated IDF curves per return period."""


class PluvialDesignEvents(ExpandMethod):
    """Rule for generating pluvial design events."""

    name: str = "pluvial_design_events"

    def __init__(
        self,
        precip_nc: Path,
        event_root: Path = Path("data/events/rainfall"),
        rps: Optional[ListOfFloat] = None,
        event_names: Optional[List[str]] = None,
        wildcard: str = "event",
        **params,
    ) -> None:
        """Create and validate a PluvialDesignEvents instance.

        Parameters
        ----------
        precip_nc : Path
            The file path to the rainfall time series in NetCDF format.
        event_root : Path, optional
            The root folder to save the derived design events, by default "data/events/rainfall".
        rps : List[float], optional
            Return periods of design events, by default [1, 2, 5, 10, 20, 50, 100].
        event_names : List[str], optional
            List of event names for the design events, by "p_event{i}", where i is the event number.
        wildcard : str, optional
            The wildcard key for expansion over the design events, by default "event".
        **params
            Additional parameters to pass to the PluvialDesignEvents Params instance.

        See Also
        --------
        :py:class:`PluvialDesignEvents Input <hydroflows.methods.rainfall.pluvial_design_events.Input>`
        :py:class:`PluvialDesignEvents Output <hydroflows.methods.rainfall.pluvial_design_events.Output>`
        :py:class:`PluvialDesignEvents Params <hydroflows.methods.rainfall.pluvial_design_events.Params>`
        """
        if rps is None:
            rps = [1, 2, 5, 10, 20, 50, 100]
        if event_names is None:
            event_names = Ref(
                ref=f"$wildcards.{wildcard}",
                value=[f"p_event{int(i+1):02d}" for i in range(len(rps))],
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
        self.input: Input = Input(precip_nc=precip_nc)
        wc = "{" + wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "pluvial_events.yml",
        )
        # set wildcards and its expand values
        self.set_expand_wildcard(wildcard, self.params.event_names)

    def run(self):
        """Run the Pluvial design events method."""
        # check if the input files and the output directory exist
        self.check_input_output_paths()

        da = xr.open_dataarray(self.input.precip_nc)
        time_dim = self.params.time_dim
        if da.ndim > 1 or time_dim not in da.dims:
            raise ValueError()

        dt = pd.Timedelta(da[time_dim].values[1] - da[time_dim].values[0])
        int(pd.Timedelta(self.params.min_dist_days, "d") / dt)

        # sample size per year
        min_sample_size = (
            pd.Timedelta(1, "A") / dt * (self.params.min_sample_perc / 100)
        )

        # specify the max event duration
        event_duration = self.params.durations[-1]

        # fit distribution per duration
        ds_idf = eva_idf(
            da,
            ev_type=self.params.ev_type,
            durations=self.params.durations,
            rps=np.maximum(1.001, self.params.rps),
            qthresh=self.params.qthresh,
            min_sample_size=min_sample_size,
        )

        ds_idf = ds_idf.assign_coords(rps=self.params.rps)
        # make sure there are no negative values
        ds_idf["return_values"] = xr.where(
            ds_idf["return_values"] < 0, 0, ds_idf["return_values"]
        )

        # Get design events hyetograph for each return period
        p_hyetograph: xr.DataArray = get_hyetograph(
            ds_idf["return_values"], dt=1, length=event_duration
        )

        # make sure there are no negative values
        p_hyetograph = xr.where(p_hyetograph < 0, 0, p_hyetograph)

        root = self.output.event_set_yaml.parent

        # save plots
        if self.params.plot_fig:
            # create a folder to save the figs
            plot_dir = Path(root, "figs")
            plot_dir.mkdir(exist_ok=True)

            _plot_hyetograph(p_hyetograph, Path(plot_dir, "rainfall_hyetograph.png"))
            _plot_idf_curves(ds_idf, Path(plot_dir, "rainfall_idf_curves.png"))

        # random starting time
        dt0 = pd.to_datetime(self.params.t0)
        time_delta = pd.to_timedelta(p_hyetograph["time"], unit="h").round("10min")
        p_hyetograph["time"] = dt0 + time_delta
        p_hyetograph = p_hyetograph.reset_coords(drop=True)

        events_list = []
        for name, rp in zip(self.params.event_names, p_hyetograph["rps"].values):
            # save p_rp as csv files
            fmt_dict = {self.params.wildcard: name}
            forcing_file = Path(str(self.output.event_csv).format(**fmt_dict))
            p_hyetograph.sel(rps=rp).to_pandas().round(2).to_csv(forcing_file)
            # save event description yaml file
            event_file = Path(str(self.output.event_yaml).format(**fmt_dict))
            event = Event(
                name=name,
                forcings=[{"type": "rainfall", "path": forcing_file.name}],
                probability=1 / rp,
            )
            event.set_time_range_from_forcings()
            event.to_yaml(event_file)
            events_list.append({"name": name, "path": event_file.name})

        # make and save event set yaml file
        event_set = EventSet(events=events_list)
        event_set.to_yaml(self.output.event_set_yaml)


def _plot_hyetograph(p_hyetograph, path: Path) -> None:
    """Plot hyetographs."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 4), sharex=True)
    p_hyetograph.rename({"rps": "Return period\n[year]"}).plot.step(
        x="time", where="mid", ax=ax
    )
    ax.set_ylabel("rainfall intensity [mm/hour]")
    ax.set_xlabel("time [hour]")
    ax.set_title("Rainfall hyetographs")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")


def _plot_idf_curves(ds_idf, path: Path) -> None:
    """Plot IDF curves."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 4), sharex=True)
    df = ds_idf["return_values"].rename({"rps": "Return period\n[year]"}).to_pandas()
    df.plot(ax=ax)
    ax.set_ylabel("rainfall intensity [mm/hour]")
    ax.set_xlabel("event duration [hour]")
    ax.set_title("Rainfall IDF curves")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")


def eva_idf(
    da: xr.DataArray,
    durations: np.ndarray = np.array([1, 2, 3, 6, 12, 24, 36, 48], dtype=int),  # noqa: B008
    distribution: str = None,
    ev_type: str = "BM",
    rps: np.ndarray = np.array([2, 5, 10, 25, 50, 100]),  # noqa: B008
    **kwargs,
) -> xr.Dataset:
    """Return IDF based on EVA. From hydromt eva dev branch.

    Return a intensity-frequency-duration (IDF) table based on block
    maxima of `da`.

    Parameters
    ----------
    da : xr.DataArray
        Timeseries data, must have a regular spaced 'time' dimension.
    durations : np.ndarray
        List of durations, provided as multiply of the data time step,
        by default [1, 2, 3, 6, 12, 24, 36, 48]
    distribution : str, optional
        Short name of distribution, by default 'gumb'
    rps : np.ndarray, optional
        Array of return periods, by default [2, 5, 10, 25, 50, 100, 250, 500]
    **kwargs :
        key-word arguments passed to the :py:meth:`eva` method.

    Returns
    -------
    xr.Dataset
        IDF table
    """
    from hydromt.stats.extremes import eva

    assert np.all(
        np.diff(durations) > 0
    ), "durations should be monotonically increasing"
    dt_max = int(durations[-1])
    da_roll = da.rolling(time=dt_max).construct("duration")
    # get mean intensity for each duration and concat into single dataarray
    da1 = [da_roll.isel(duration=slice(0, d)).mean("duration") for d in durations]
    da1 = xr.concat(da1, dim="duration")
    da1["duration"] = xr.IndexVariable("duration", durations)
    # return
    if "min_dist" not in kwargs:
        kwargs.update(min_dist=dt_max)
    return eva(da1, ev_type=ev_type, distribution=distribution, rps=rps, **kwargs)


def get_hyetograph(da_idf: xr.DataArray, dt: float, length: int) -> xr.DataArray:
    """Return hyetograph.

    Return design storm hyetograph based on intensity-frequency-duration (IDF)
    table. From hydromt eva dev branch.

    The input `da_idf` can be obtained as the output of the :py:meth:`eva_idf`.
    Note: here we use the precipitation intensity and not the depth as input!
    The design hyetograph is based on the alternating block method.

    Parameters
    ----------
    da_idf : xr.DataArray
        IDF data, must contain a 'duration' dimension
    dt : float
        Time-step for output hyetograph, same time step unit as IDF duration.
    length : int
        Number of time-step intervals in design storms.

    Returns
    -------
    xr.DataArray
        Design storm hyetograph
        #TODO: add some description of the variables and dimensions...(check below)
        The design storms time dimension is relative to the peak (time=0) of time step
        dt and total length record of length.
        If using :py:meth:`eva_idf` to obtain the IDF curves, the output is stored in
        variable `return_values`.
    """
    durations = da_idf["duration"]
    assert np.all(np.diff(durations) > 0)
    assert dt >= durations[0]

    t = np.arange(0, durations[-1] + dt, dt)
    alt_order = np.append(np.arange(1, length, 2)[::-1], np.arange(0, length, 2))

    # drop 'time' dimension if present in xarray.Dataset
    if "time" in list(da_idf.dims):
        da_idf = da_idf.drop_dims("time")
    # get cummulative precip depth
    pdepth = (da_idf * durations).reset_coords(drop=True).rename({"duration": "time"})
    # interpolate to dt temporal resolution
    # load required for argsort on next line
    pstep = (pdepth.interp(time=t).fillna(0).diff("time") / dt).load()
    # FIXME make sure pstep is decreasing with time;
    pstep.data = np.take_along_axis(pstep.values, pstep.argsort(axis=0), axis=0)[
        ::-1, :
    ]
    # reorder using alternating blocks method
    pevent = pstep.isel(time=slice(0, length)).isel(time=alt_order)
    # set time coordinate
    t0 = int(np.ceil((length + 1) / 2))
    pevent["time"] = xr.IndexVariable("time", (t[1 : length + 1] - t0))
    pevent.attrs.update(**da_idf.attrs)
    return pevent
