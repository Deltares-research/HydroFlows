"""Wflow design hydrograph method."""

import os
from pathlib import Path
from typing import List, Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from hydromt.stats import design_events, extremes, get_peaks
from pydantic import BaseModel

from hydroflows._typing import ListOfFloat
from hydroflows.events import Event, EventCatalog
from hydroflows.methods.method import ExpandMethod

__all__ = ["WflowDesignHydro"]


class Input(BaseModel):
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


class Output(BaseModel):
    """Output parameters for the :py:class:`WflowDesignHydro` method."""

    events: List[str]
    """List of event names derived from the design events."""

    event_yaml: Path
    """The path to the event description file,
    see also :py:class:`hydroflows.workflows.events.Event`."""

    event_csv: Path
    """The path to the event csv timeseries file."""

    event_catalog: Path
    """The path to the event catalog yml file,
    see also :py:class:`hydroflows.workflows.events.EventCatalog` class.
    """


class Params(BaseModel):
    """Parameters for the :py:class:`WflowDesignHydro` method.

    See Also
    --------
    :py:class:`hydromt.stats.extremes`
        For more details on the event selection, EVA and peak hydrographs
        using HydroMT.
    """

    event_root: Path
    """"Root folder to save the derived design events."""

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

    # return periods of interest
    rps: ListOfFloat = [1, 2, 5, 10, 20, 50, 100]
    """Return periods of interest."""

    plot_fig: bool = True
    """Determines whether to plot figures, including the derived design hydrograph
    per location and return period, as well as the EVA fits."""

    # duration for hydrograph
    wdw_size_days: int = 6
    """Duration for hydrograph in days."""


class WflowDesignHydro(ExpandMethod):
    """Rule for generating fluvial design events."""

    name: str = "wflow_design_hydro"
    expand_refs: dict = {"event": "events"}

    def __init__(
        self, discharge_nc: Path, event_root: Path = "data/events/discharge", **params
    ) -> None:
        """Create and validate a WflowDesignHydro instance.

        Parameters
        ----------
        discharge_nc : Path
            The file path to the discharge time series in NetCDF format.
        event_root : Path, optional
            The root folder to save the derived design events, by default "data/events/discharge".
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
        self.params: Params = Params(event_root=event_root, **params)
        self.input: Input = Input(discharge_nc=discharge_nc)
        self.output: Output = Output(
            events=[f"q_event{int(i+1):02d}" for i in range(len(self.params.rps))],
            event_yaml=Path(event_root, "{event}.yml"),
            event_csv=Path(event_root, "{event}.csv"),
            event_catalog=Path(event_root, "event_catalog.yml"),
        )

    def run(self):
        """Run the WflowDesignHydro method."""
        # check if the input files and the output directory exist
        self.check_input_output_paths()
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
        q_hydrograph = da_q_hydrograph.mean("peak") * da_rps

        # make sure there are no negative values
        q_hydrograph = xr.where(q_hydrograph < 0, 0, q_hydrograph)

        # save plots
        root = self.output.event_catalog.parent
        os.makedirs(root, exist_ok=True)

        if self.params.plot_fig:
            fn_plots = os.path.join(root, "figs")

            os.makedirs(fn_plots, exist_ok=True)

            # loop through all the stations and save figs
            for station in da[index_dim].values:
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
                    rps=np.maximum(1.001, self.params.rps),
                    extremes_rate=extremes_rate,
                    ax=ax,
                )

                ax.set_title(f"Station {station}")
                ax.set_ylabel(R"Discharge [m$^{3}$ s$^{-1}$]")
                ax.set_xlabel("Return period [years]")
                ax.grid(True)
                fig.tight_layout()
                fig.savefig(
                    os.path.join(fn_plots, f"return_values_q_{station}.png"),
                    dpi=150,
                    bbox_inches="tight",
                )

                # Plot hydrographs
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
                    os.path.join(fn_plots, f"discharge_hydrograph_{station}.png"),
                    dpi=150,
                    bbox_inches="tight",
                )

        # Put a random date for the csvs
        dt0 = pd.to_datetime(self.params.t0)
        time_delta = pd.to_timedelta(q_hydrograph["time"], unit=unit)
        q_hydrograph["time"] = dt0 + time_delta
        q_hydrograph = q_hydrograph.reset_coords(drop=True)

        events_list = []
        for name, rp in zip(self.output.events, q_hydrograph.rps.values):
            # save q_rp as csv files
            q_hydrograph.sel(rps=rp).to_pandas().round(2).to_csv(
                str(self.output.event_csv).format(event=name)
            )

            # save event description file
            event = Event(
                name=name,
                forcings=[{"type": "discharge", "path": f"{name}.csv"}],
                probability=1 / rp,
            )
            event.set_time_range_from_forcings()
            event.to_yaml(str(self.output.event_yaml).format(event=name))
            events_list.append(event)

        # make a data catalog
        event_catalog = EventCatalog(
            root=root,
            events=events_list,
        )
        event_catalog.to_yaml(self.output.event_catalog)
