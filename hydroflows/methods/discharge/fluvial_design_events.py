"""Derive fluvial design events from a discharge time series."""


import os
from pathlib import Path
from typing import List, Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from hydromt.stats import design_events, extremes, get_peaks
from pydantic import PositiveInt, model_validator

from hydroflows._typing import FileDirPath, ListOfFloat, ListOfStr, OutputDirPath
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["FluvialDesignEvents", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`FluvialDesignEvents` method."""

    discharge_nc: Path
    """The file path to the discharge time series in NetCDF format which is used
    to apply EVA and derive design events. This file should contain an index dimension and a time
    dimension for several (gauge) locations.

    - The discharge time series can be produced either by the Wflow toolchain (via the
      :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowBuild`,
      :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing`, and
      :py:class:`hydroflows.methods.wflow.wflow_run.WflowRun` methods) or can be directly supplied by the user.

    - When the design events are used in Sfincs using the
      :py:class:`hydroflows.methods.sfincs.sfincs_update_forcing.SfincsUpdateForcing` method,
      the index dimension should correspond to the index of the Sfincs source points, providing the corresponding
      time series at specific locations.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`FluvialDesignEvents` method."""

    event_yaml: FileDirPath
    """The path to the event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_csv: Path
    """The path to the event csv timeseries file."""

    event_set_yaml: FileDirPath
    """The path to the event set yml file that contains the derived
    fluvial event configurations. This event set can be created from
    a dictionary using the :py:class:`hydroflows.events.EventSet` class.
    """


class Params(Parameters):
    """Parameters for the :py:class:`FluvialDesignEvents` method.

    See Also
    --------
    :py:class:`hydromt.stats.extremes`
        For more details on the event selection, EVA and peak hydrographs
        using HydroMT.
    """

    event_root: OutputDirPath
    """"Root folder to save the derived design events."""

    rps: ListOfFloat
    """Return periods of of design events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    # Note: set by model_validator based on rps if not provided
    event_names: Optional[ListOfStr] = None
    """List of event names derived from the design events."""

    # parameters for the get_peaks function
    ev_type: Literal["BM", "POT"] = "BM"
    """Method to select events/peaks. Valid options are 'BM' for block maxima or
    'POT' for Peak over threshold."""

    min_dist_days: int = 7
    """Minimum distance between events/peaks measured in days."""

    qthresh: float = 0.95
    """Quantile threshold used with peaks over threshold method."""

    min_sample_perc: int = 80
    """Minimum sample percentage in a valid block. Peaks of invalid bins are set to NaN"""

    var_name: str = "Q"
    """Name of the discharge time series variable provided in :py:class:`Input` class"""

    index_dim: str = "Q_gauges"
    """Index dimension of the input time series provided in :py:class:`Input` class."""

    time_dim: str = "time"
    """Time dimension of the input time series provided in :py:class:`Input` class."""

    t0: str = "2020-01-01"
    """Random initial date for the design events."""

    warm_up_years: PositiveInt = None
    """The number of initial years (positive integer) to exclude from the discharge time series
    as a warm-up period, typically used when the data is generated through
    hydrological modeling and requires an initial warm-up phase."""

    n_peaks: int = None
    """Number of largest peaks to get hydrograph.
    If None (default) all peaks are used."""

    plot_fig: bool = True
    """Determines whether to plot figures, including the derived design hydrograph
    per location and return period, as well as the EVA fits."""

    # duration for hydrograph
    wdw_size_days: int = 6
    """Duration for hydrograph in days."""

    @model_validator(mode="after")
    def _validate_event_names(self):
        """Use rps to define event names if not provided."""
        if self.event_names is None:
            self.event_names = [f"q_event{int(i+1):02d}" for i in range(len(self.rps))]
        elif len(self.event_names) != len(self.rps):
            raise ValueError("event_names should have the same length as rps")
        # create a reference to the event wildcard
        if "event_names" not in self._refs:
            self._refs["event_names"] = f"$wildcards.{self.wildcard}"
        return self


class FluvialDesignEvents(ExpandMethod):
    """Derive fluvial design events from a discharge time series.

    Parameters
    ----------
    discharge_nc : Path
        The file path to the discharge time series in NetCDF format.
    event_root : Path, optional
        The root folder to save the derived design events, by default "data/events/discharge".
    rps : List[float], optional
        Return periods of the design events, by default [1, 2, 5, 10, 20, 50, 100].
    event_names : List[str], optional
        List of event names of the design events, by default "q_event{i}", where i is the event number.
    wildcard : str, optional
        The wildcard key for expansion over the design events, by default "event".
    **params
        Additional parameters to pass to the FluvialDesignEvents Params instance.
        See :py:class:`fluvial_design_events Params <hydroflows.methods.discharge.fluvial_design_events.Params>`.

    See Also
    --------
    :py:class:`fluvial_design_events Input <hydroflows.methods.discharge.fluvial_design_events.Input>`
    :py:class:`fluvial_design_events Output <hydroflows.methods.discharge.fluvial_design_events.Output>`
    :py:class:`fluvial_design_events Params <hydroflows.methods.discharge.fluvial_design_events.Params>`
    :py:class:`hydromt.stats.extremes`
    """

    name: str = "fluvial_design_events"

    _test_kwargs = {
        "discharge_nc": Path("discharge.nc"),
    }

    def __init__(
        self,
        discharge_nc: Path,
        event_root: Path = "data/events/discharge",
        rps: Optional[List[float]] = None,
        event_names: Optional[List[str]] = None,
        wildcard: str = "event",
        **params,
    ) -> None:
        if rps is None:
            rps = [1, 2, 5, 10, 20, 50, 100]
        self.params: Params = Params(
            event_root=event_root,
            rps=rps,
            event_names=event_names,
            wildcard=wildcard,
            **params,
        )
        self.input: Input = Input(discharge_nc=discharge_nc)
        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "fluvial_design_events.yml",
        )
        # set wildcard
        self.set_expand_wildcard(wildcard, self.params.event_names)

    def _run(self):
        """Run the FluvialDesignEvents method."""
        root = self.output.event_set_yaml.parent

        # read the provided time series
        da = xr.open_dataset(self.input.discharge_nc)[self.params.var_name]
        time_dim = self.params.time_dim
        index_dim = self.params.index_dim
        # check if dims in da
        for dim in [time_dim, index_dim]:
            if dim not in da.dims:
                raise ValueError(f"{dim} not a dimension in, {self.input.discharge_nc}")

        # Check if warm_up_years is not None
        if self.params.warm_up_years is not None:
            # warm up period from the start of the time series up to warm_up_years to exclude
            warm_up_period = da[time_dim].values[0] + pd.Timedelta(
                self.params.warm_up_years, "A"
            )
            # Keep timeseries only after the warm-up period
            da = da.sel({time_dim: slice(warm_up_period, None)})

            if da[time_dim].size == 0:
                raise ValueError(
                    f"Selection resulted in an empty time series after warm-up period of {self.params.warm_up_years} years."
                )

        # find the timestep of the input time series
        dt = pd.Timedelta(da[time_dim].values[1] - da[time_dim].values[0])

        # TODO automate the option to include different timesteps
        if (dt.total_seconds() / 86400) == 1:
            unit = "days"
        elif (dt.total_seconds() / 3600) == 1:
            unit = "hours"
        else:
            # Raise an error if the resolution is not hourly or daily
            raise ValueError(
                "The resolution of the input time series should be hourly or daily"
            )

        # convert min_dist from days (min_dist_days param) to time series time steps
        min_dist = int(pd.Timedelta(self.params.min_dist_days, "d") / dt)

        # convert wdw_size from days (wdw_size_days param) to time series time steps
        wdw_size = int(pd.Timedelta(self.params.wdw_size_days, "d") / dt)

        # specify the setting for extracting peaks
        kwargs = {}
        if self.params.ev_type == "POT":
            kwargs = dict(min_dist=min_dist, qthresh=self.params.qthresh, period="year")
        elif self.params.ev_type == "BM":
            # sample size per year
            min_sample_size = (
                pd.Timedelta(365.25, "d") / dt * (self.params.min_sample_perc / 100)
            )
            kwargs = dict(
                min_dist=min_dist, period="year", min_sample_size=min_sample_size
            )
        else:
            # Raise an error when ev_type is neither "POT" nor "BM"
            raise ValueError("Invalid EVA type")

        # derive the peak
        da_peaks = get_peaks(
            da, ev_type=self.params.ev_type, time_dim=time_dim, **kwargs
        )

        # TODO reduce da_peaks to n year samples in case of POT

        # specify and fit an EV distribution
        da_params = extremes.fit_extremes(da_peaks, ev_type=self.params.ev_type).load()
        if index_dim not in da_params.dims:
            da_params = da_params.expand_dims(index_dim)

        # calculate return values for specified rps/params
        da_rps = extremes.get_return_value(
            da_params, rps=np.maximum(1.001, self.params.rps)
        ).load()
        # in case rps has one value expand dims
        if len(self.params.rps) == 1:
            da_rps = da_rps.expand_dims(dim={"rps": self.params.rps})
        else:
            da_rps = da_rps.assign_coords(rps=self.params.rps)
        # hydrographs based on the n highest peaks
        dims = [time_dim, "peak", index_dim]
        da_q_hydrograph = design_events.get_peak_hydrographs(
            da,
            da_peaks,
            wdw_size=wdw_size,
            n_peaks=self.params.n_peaks,
        )
        if index_dim not in da_q_hydrograph.dims:
            da_q_hydrograph = da_q_hydrograph.expand_dims(index_dim)
        da_q_hydrograph = da_q_hydrograph.transpose(*dims)

        # calculate the mean design hydrograph per rp
        q_hydrograph: xr.DataArray = da_q_hydrograph.mean("peak") * da_rps

        # make sure there are no negative values
        q_hydrograph = xr.where(q_hydrograph < 0, 0, q_hydrograph)

        # Use T0 for csv time series
        dt0 = pd.to_datetime(self.params.t0)
        time_delta = pd.to_timedelta(q_hydrograph["time"], unit=unit)
        q_hydrograph["time"] = dt0 + time_delta
        q_hydrograph = q_hydrograph.reset_coords(drop=True)

        events_list = []
        for name, rp in zip(self.params.event_names, q_hydrograph["rps"].values):
            output = self.get_output_for_wildcards({self.params.wildcard: name})
            q_df = q_hydrograph.sel(rps=rp).to_pandas().reset_index()
            q_df = q_df.rename(
                dict(zip(q_df.columns, ("time", *da[index_dim].values))), axis=1
            )
            q_df.to_csv(output["event_csv"], index=False)
            # save event yaml file
            event = Event(
                name=name,
                forcings=[{"type": "discharge", "path": output["event_csv"]}],
                return_period=rp,
            )
            event.set_time_range_from_forcings()
            event.to_yaml(output["event_yaml"])
            events_list.append({"name": name, "path": output["event_yaml"]})

        # make and save event set yaml file
        event_set = EventSet(events=events_list)
        event_set.to_yaml(self.output.event_set_yaml)

        # save plots
        if self.params.plot_fig:
            plot_dir = os.path.join(root, "figs")
            os.makedirs(plot_dir, exist_ok=True)

            # loop through all the stations and save figs
            for station in da[index_dim].values:
                # Plot EVA
                plot_eva(
                    da_peaks.sel({index_dim: station}),
                    da_params.sel({index_dim: station}),
                    self.params.rps,
                    station,
                    plot_dir,
                )

                # Plot hydrographs
                plot_hydrograph(
                    q_hydrograph.sel({index_dim: station}), station, unit, plot_dir
                )


def plot_eva(da_peaks, da_params, rps, station, plot_dir):
    fig, ax = plt.subplots(1, 1, figsize=(7, 5))

    extremes_rate = da_peaks["extremes_rate"].item()
    dist = da_params["distribution"].item()

    # Plot return values fits
    extremes.plot_return_values(
        da_peaks.where(~np.isnan(da_peaks), drop=True),
        da_params,
        dist,
        color="k",
        nsample=1000,
        rps=np.maximum(1.001, rps),
        extremes_rate=extremes_rate,
        ax=ax,
    )

    ax.set_title(f"Station {station}")
    ax.set_ylabel(R"Discharge [m$^{3}$ s$^{-1}$]")
    ax.set_xlabel("Return period [years]")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(
        os.path.join(plot_dir, f"return_values_q_{station}.png"),
        dpi=150,
        bbox_inches="tight",
    )


def plot_hydrograph(q_hydrograph, station, unit, plot_dir):
    fig, ax = plt.subplots(1, 1, figsize=(7, 5))
    q_hydrograph.rename({"rps": "return period\n[years]"}).to_pandas().plot(ax=ax)  # noqa: E501
    ax.set_xlabel(f"Time [{unit}]")
    ax.set_title(f"Station {station}")
    ax.set_ylabel(R"Discharge [m$^{3}$ s$^{-1}$]")
    fig.tight_layout()
    ax.grid(True)
    fig.savefig(
        os.path.join(plot_dir, f"discharge_hydrograph_{station}.png"),
        dpi=150,
        bbox_inches="tight",
    )
