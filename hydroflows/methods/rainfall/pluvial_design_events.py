"""Pluvial design events method."""

from pathlib import Path
from typing import Dict, List, Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from pydantic import model_validator

from hydroflows._typing import (
    FileDirPath,
    ListOfFloat,
    ListOfInt,
    ListOfStr,
    OutputDirPath,
)
from hydroflows.methods.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["PluvialDesignEvents", "Input", "Output", "Params"]


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

    event_yaml: FileDirPath
    """The path to the event description file,
    see also :py:class:`hydroflows.methods.events.Event`."""

    event_csv: Path
    """The path to the event csv timeseries file"""

    event_set_yaml: FileDirPath
    """The path to the event set yml file,
    see also :py:class:`hydroflows.methods.events.EventSet`.
    """


class Params(Parameters):
    """Parameters for :py:class:`PluvialDesignEvents` method."""

    event_root: OutputDirPath
    """Root folder to save the derived design events."""

    rps: ListOfInt
    """Return periods of interest."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    # Note: set by model_validator based on rps if not provided
    event_names: Optional[ListOfStr] = None
    """List of event names associated with return periods."""

    duration: int = 48
    """Duration of the produced design event."""

    timesteps: ListOfInt = [1, 2, 3, 6, 12, 24, 36, 48]
    """Intensity Duration Frequencies provided as multiply of the data time step."""

    min_dist_days: int = 0
    """Minimum distance between events/peaks measured in days."""

    ev_type: Literal["BM", "POT"] = "BM"
    """Method to select events/peaks. Valid options are 'BM' for block
    maxima or 'POT' for Peak over threshold."""

    distribution: Optional[str] = None
    """Type of extreme value distribution corresponding with `ev_type`.
    Options are "gumb" or "gev" for BM, and "exp" or "gpd" for POT.
    If None (default) is used, "gumb" is selected for BM and "exp" for POT."""

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

    fig_name_hyeto: str = "rainfall_hyetographs"
    """Name of the design hyetographs figure."""

    fig_name_idf: str = "rainfall_idf_curves"
    """Name of the idf figure."""

    save_idf_csv: bool = True
    """Determines whether to save the calculated IDF curve values
    per return period in a csv format."""

    @model_validator(mode="after")
    def _validate_model(self):
        # validate event_names
        if self.event_names is None:
            self.event_names = [f"p_event_rp{rp:03d}" for rp in self.rps]
        elif len(self.event_names) != len(self.rps):
            raise ValueError("event_names should have the same length as rps")
        # create a reference to the event wildcard
        if "event_names" not in self._refs:
            self._refs["event_names"] = f"$wildcards.{self.wildcard}"

        # validate distribution
        acceptable_distributions: Dict[str, list] = {
            "BM": ["gumb", "gev"],
            "POT": ["exp", "gpd"],
        }
        if self.distribution is None:
            acceptable_distributions.get(self.ev_type)[0]
        else:
            # Get the acceptable set of distributions for the current ev_type
            valid_distributions = acceptable_distributions.get(self.ev_type)
            # Check if the provided distribution is in the set of valid options
            if self.distribution not in valid_distributions:
                raise ValueError(
                    f"For ev_type '{self.ev_type}', distribution must be one of {valid_distributions}."
                )
        if self.duration > max(self.timesteps):
            raise ValueError(
                f"Duration {self.duration} exceeds the maximum specified value {max(self.timesteps)} "
                f"from the list of timesteps: {self.timesteps}."
            )
        return self


class PluvialDesignEvents(ExpandMethod):
    """Method for generating pluvial design events from rainfall timeseries.

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
    ev_type: Literal["BM", "POT"]
        Method to select events/peaks. Valid options are 'BM' (default)
        for block maxima or 'POT' for Peak over threshold.
    distribution : str, optional
        Type of extreme value distribution corresponding with `ev_type`.
        Options are "gumb" or "gev" for BM, and "exp" or "gpd" for POT.
        If None (default) is used, "gumb" is selected for BM and "exp" for POT.
    wildcard : str, optional
        The wildcard key for expansion over the design events, by default "event".
    duration : int
        Duration of the produced design event, by default 48 hours.
    **params
        Additional parameters to pass to the PluvialDesignEvents Params instance.

    See Also
    --------
    :py:class:`PluvialDesignEvents Input <hydroflows.methods.rainfall.pluvial_design_events.Input>`
    :py:class:`PluvialDesignEvents Output <hydroflows.methods.rainfall.pluvial_design_events.Output>`
    :py:class:`PluvialDesignEvents Params <hydroflows.methods.rainfall.pluvial_design_events.Params>`
    """

    name: str = "pluvial_design_events"

    _test_kwargs = {
        "precip_nc": Path("precip.nc"),
    }

    def __init__(
        self,
        precip_nc: Path,
        event_root: Path = Path("data/events/rainfall"),
        rps: Optional[ListOfFloat] = None,
        event_names: Optional[List[str]] = None,
        ev_type: Literal["BM", "POT"] = "BM",
        distribution: Optional[str] = None,
        wildcard: str = "event",
        duration: int = 48,
        **params,
    ) -> None:
        if rps is None:
            rps = [2, 5, 10, 20, 50, 100]
        self.params: Params = Params(
            event_root=event_root,
            rps=rps,
            event_names=event_names,
            ev_type=ev_type,
            distribution=distribution,
            wildcard=wildcard,
            duration=duration,
            **params,
        )
        self.input: Input = Input(precip_nc=precip_nc)
        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "pluvial_design_events.yml",
        )
        # set wildcards and its expand values
        self.set_expand_wildcard(wildcard, self.params.event_names)

    def _run(self):
        """Run the Pluvial design events method."""
        da = xr.open_dataarray(self.input.precip_nc)
        time_dim = self.params.time_dim
        if da.ndim > 1 or time_dim not in da.dims:
            raise ValueError()

        dt = pd.Timedelta(da[time_dim].values[1] - da[time_dim].values[0])
        int(pd.Timedelta(self.params.min_dist_days, "d") / dt)

        # sample size per year
        min_sample_size = (
            pd.Timedelta(365.25, "d") / dt * (self.params.min_sample_perc / 100)
        )

        # fit distribution per duration
        ds_idf = eva_idf(
            da,
            ev_type=self.params.ev_type,
            distribution=self.params.distribution,
            durations=self.params.timesteps,
            rps=np.maximum(1.001, self.params.rps),
            qthresh=self.params.qthresh,
            min_sample_size=min_sample_size,
        )

        # keep durations up to the max user defined duration
        ds_idf = ds_idf.sel(duration=slice(None, self.params.duration))
        ds_idf = ds_idf.assign_coords(rps=self.params.rps)
        # in case rps has one value expand return values dim
        if len(self.params.rps) == 1:
            return_values_expanded = ds_idf.return_values.expand_dims(
                rps=ds_idf.rps.values
            )
            # this is needed later for df conversion and plotting
            return_values_expanded = return_values_expanded.transpose("duration", "rps")
            ds_idf = ds_idf.assign(return_values=return_values_expanded)
        # make sure there are no negative values
        ds_idf["return_values"] = xr.where(
            ds_idf["return_values"] < 0, 0, ds_idf["return_values"]
        )

        if self.params.save_idf_csv:
            df_idf = (
                ds_idf["return_values"]
                .rename({"rps": "Return period\n[year]"})
                .to_pandas()
            )
            df_idf.to_csv(Path(self.output.event_csv.parent, "idf.csv"), index=True)

        # Get design events hyetograph for each return period
        p_hyetograph: xr.DataArray = get_hyetograph(ds_idf["return_values"])

        # make sure there are no negative values
        p_hyetograph = xr.where(p_hyetograph < 0, 0, p_hyetograph)

        root = self.output.event_set_yaml.parent

        # save plots
        if self.params.plot_fig:
            # create a folder to save the figs
            plot_dir = Path(root, "figs")
            plot_dir.mkdir(exist_ok=True)

            _plot_hyetograph(
                p_hyetograph, Path(plot_dir, f"{self.params.fig_name_hyeto}.png")
            )
            _plot_idf_curves(
                ds_idf["return_values"],
                Path(plot_dir, f"{self.params.fig_name_idf}.png"),
            )

        # random starting time
        dt0 = pd.to_datetime(self.params.t0)
        time_delta = pd.to_timedelta(p_hyetograph["time"], unit="h").round("10min")
        p_hyetograph["time"] = dt0 + time_delta
        p_hyetograph = p_hyetograph.reset_coords(drop=True)

        events_list = []
        for name, rp in zip(self.params.event_names, p_hyetograph["rps"].values):
            output = self.get_output_for_wildcards({self.params.wildcard: name})
            p_hyetograph.sel(rps=rp).to_pandas().round(2).to_csv(output["event_csv"])
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


def _plot_hyetograph(p_hyetograph, path: Path, rp_dim="rps") -> None:
    """Plot hyetographs."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 4), sharex=True)
    p_hyetograph.rename({rp_dim: "Return period\n[year]"}).plot.step(
        x="time", where="mid", ax=ax
    )
    ax.set_ylabel("rainfall intensity [mm/hour]")
    ax.set_xlabel("time [hour]")
    ax.set_title("Rainfall hyetographs")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")


def _plot_idf_curves(da_idf, path: Path, rp_dim="rps") -> None:
    """Plot IDF curves."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 4), sharex=True)
    df = da_idf.rename({rp_dim: "Return period\n[year]"}).to_pandas()
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
        Short name of distribution, by default 'None'
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


def get_hyetograph(da_idf: xr.DataArray, intensity_dim="duration") -> xr.DataArray:
    """Return hyetograph.

    Return design storm hyetograph based on intensity-frequency-duration (IDF)
    table. From hydromt eva dev branch.

    The input `da_idf` can be obtained as the output of the :py:meth:`eva_idf`.
    Note: here we use the precipitation intensity and not the depth as input!
    The design hyetograph is based on the alternating block method.

    Parameters
    ----------
    da_idf : xr.DataArray
        IDF data, with a duration dimension
    intensity_dim : str
        Intensity dimension of the input da_idf.

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
    assert (
        intensity_dim in da_idf.dims
    ), f"{intensity_dim} not a dimension in the input IDF data"
    durations = da_idf[intensity_dim]
    dt = durations.values[0]
    length = int(durations.values[-1] / dt)
    assert np.all(np.diff(durations) > 0)
    if da_idf.ndim == 1:
        da_idf = da_idf.expand_dims("event", -1)

    t = np.arange(0, durations[-1] + dt, dt)
    alt_order = np.append(np.arange(1, length, 2)[::-1], np.arange(0, length, 2))

    # drop 'time' dimension if present in xarray.Dataset
    if "time" in list(da_idf.dims):
        da_idf = da_idf.drop_dims("time")
    # get cummulative precip depth
    pdepth = (
        (da_idf * durations).reset_coords(drop=True).rename({intensity_dim: "time"})
    )
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
    pevent["time"] = xr.IndexVariable("time", (t[1 : length + 1] - t[-1] / 2 - dt))
    pevent.attrs.update(**da_idf.attrs)
    return pevent
