"""Wflow design hydrograph method."""

import os
from pathlib import Path
from typing import Any, List, Literal, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from hydromt.stats import design_events, extremes, get_peaks
from pydantic import ValidationInfo, field_validator, model_validator

from hydroflows._typing import ListOfFloat, ListOfStr
from hydroflows.events import Event, EventSet
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters
from hydroflows.workflow.reference import Ref

__all__ = ["WflowDesignHydro"]


class Input(Parameters):
    """Input parameters for the :py:class:`WflowDesignHydro` method."""

    discharge_nc: Path
    """The file path to the discharge time series in NetCDF format which are used
    to apply EVA and derive design events. This file contains an index dimension and a time
    dimension for several Sfincs boundary points, .

    - The index dimension corresponds to the index of the Sfincs source points, providing the corresponding time
      series at specific locations.
    - This time series can be produced either by the Wflow toolchain (via the
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowBuild`,
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing`, and
    :py:class:`hydroflows.methods.wflow.wflow_run.WflowRun` methods) or can be directly supplied by the user.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`WflowDesignHydro` method."""

    event_yaml: Path
    """The path to the event description file,
    see also :py:class:`hydroflows.events.Event`."""

    event_csv: Path
    """The path to the event csv timeseries file."""

    event_set_yaml: Path
    """The path to the event set yml file that contains the derived
    fluvial event configurations. This event set can be created from
    a dictionary using the :py:class:`hydroflows.events.EventSet` class.
    """


class Params(Parameters):
    """Parameters for the :py:class:`WflowDesignHydro` method.

    See Also
    --------
    :py:class:`hydromt.stats.extremes`
        For more details on the event selection, EVA and peak hydrographs
        using HydroMT.
    """

    event_root: Path
    """"Root folder to save the derived design events."""

    rps: ListOfFloat
    """Return periods of of design events."""

    wildcard: str = "event"
    """The wildcard key for expansion over the design events."""

    # Note: requires rps and wildcard which should be defined before this
    event_names: ListOfStr
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

    index_dim: str = "Q_gauges"
    """Index dimension of the input time series provided in :py:class:`Input` class."""

    time_dim: str = "time"
    """Time dimension of the input time series provided in :py:class:`Input` class."""

    t0: str = "2020-01-01"
    """Random initial date for the design events."""

    warm_up_years: int = 2
    """Number of (initial) years to exclude from the discharge timeseries
    as a warm-up period."""

    n_peaks: int = None
    """Number of largest peaks to get hydrograph.
    If None (default) all peaks are used."""

    plot_fig: bool = True
    """Determines whether to plot figures, including the derived design hydrograph
    per location and return period, as well as the EVA fits."""

    # duration for hydrograph
    wdw_size_days: int = 6
    """Duration for hydrograph in days."""

    @field_validator("event_names", mode="before")
    @classmethod
    def _validate_event_names(cls, v: Any, info: ValidationInfo):
        """Use rps to define event names if not provided."""
        if v is None:
            rps = info.data["rps"]
            wildcard = info.data["wildcard"]
            v = Ref(
                ref=f"$wildcards.{wildcard}",
                value=[f"q_event{int(i+1):02d}" for i in range(len(rps))],
            )
        return v

    @model_validator(mode="after")
    def _calculate_keys(self) -> Any:
        if len(self.event_names) != len(self.rps):
            raise ValueError("event_names should have the same length as rps")


class WflowDesignHydro(ExpandMethod):
    """Rule for generating fluvial design events."""

    name: str = "wflow_design_hydro"

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
        """Create and validate a WflowDesignHydro instance.

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
            Additional parameters to pass to the WflowDesignHydro Params instance.
            See :py:class:`wflow_design_hydro Params <hydroflows.methods.wflow.wflow_design_hydro.Params>`.

        See Also
        --------
        :py:class:`wflow_design_hydro Input <hydroflows.methods.wflow.wflow_design_hydro.Input>`
        :py:class:`wflow_design_hydro Output <hydroflows.methods.wflow.wflow_design_hydro.Output>`
        :py:class:`wflow_design_hydro Params <hydroflows.methods.wflow.wflow_design_hydro.Params>`
        :py:class:`hydromt.stats.extremes`
            For more details on the event selection, EVA and peak hydrographs
            using HydroMT.
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
        self.input: Input = Input(discharge_nc=discharge_nc)
        wc = "{" + self.params.wildcard + "}"
        self.output: Output = Output(
            event_yaml=self.params.event_root / f"{wc}.yml",
            event_csv=self.params.event_root / f"{wc}.csv",
            event_set_yaml=self.params.event_root / "fluvial_events.yml",
        )
        # set wildcard
        self.set_expand_wildcard(wildcard, self.params.event_names)

    def run(self):
        """Run the WflowDesignHydro method."""
        root = self.output.event_set_yaml.parent

        # read the provided wflow time series
        da = xr.open_dataarray(self.input.discharge_nc)
        time_dim = self.params.time_dim
        index_dim = self.params.index_dim
        # check if dims in da
        for dim in [time_dim, index_dim]:
            if dim not in da.dims:
                raise ValueError(f"{dim} not a dimension in, {self.input.discharge_nc}")
        # warm up period from the start of the time series up to warm_up_years to exclude
        warm_up_period = da[time_dim].values[0] + pd.Timedelta(
            self.params.warm_up_years, "A"
        )
        # keep timeseries only after the warm up period
        da = da.sel({time_dim: slice(warm_up_period, None)})

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
                pd.Timedelta(1, "A") / dt * (self.params.min_sample_perc / 100)
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

        # calculate return values for specified rps/params
        da_rps = extremes.get_return_value(
            da_params, rps=np.maximum(1.001, self.params.rps)
        ).load()
        da_rps = da_rps.assign_coords(rps=self.params.rps)

        # hydrographs based on the n highest peaks
        da_q_hydrograph = design_events.get_peak_hydrographs(
            da,
            da_peaks,
            wdw_size=wdw_size,
            n_peaks=self.params.n_peaks,
        ).transpose(time_dim, "peak", index_dim)

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
            fmt_dict = {self.params.wildcard: name}
            # save q_rp as csv file
            forcing_file = Path(str(self.output.event_csv).format(**fmt_dict))
            q_hydrograph.sel(rps=rp).to_pandas().round(2).to_csv(forcing_file)
            # save event yaml file
            event_file = Path(str(self.output.event_yaml).format(**fmt_dict))
            event = Event(
                name=name,
                forcings=[{"type": "discharge", "path": forcing_file.name}],
                probability=1 / rp,
            )
            event.set_time_range_from_forcings()
            event.to_yaml(event_file)
            events_list.append({"name": name, "path": event_file.name})

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
                    da_peaks, da_params, self.params.rps, index_dim, station, plot_dir
                )

                # Plot hydrographs
                plot_hydrograph(q_hydrograph, station, index_dim, unit, plot_dir)


def plot_eva(da_peaks, da_params, rps, index_dim, station, plot_dir):
    fig, ax = plt.subplots(1, 1, figsize=(7, 5))

    extremes_rate = da_peaks.sel({index_dim: station}).extremes_rate.item()
    dist = da_params.sel({index_dim: station}).distribution.item()

    # Plot return values fits
    extremes.plot_return_values(
        da_peaks.sel({index_dim: station}),
        da_params.sel({index_dim: station}),
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


def plot_hydrograph(q_hydrograph, station, index_dim, unit, plot_dir):
    fig, ax = plt.subplots(1, 1, figsize=(7, 5))
    q_hydrograph.sel({index_dim: station}).rename(
        {"rps": "return period\n[years]"}
    ).to_pandas().plot(ax=ax)  # noqa: E501
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
