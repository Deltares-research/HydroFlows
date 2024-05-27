"""Wflow design hydrograph method."""

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from hydromt.stats import design_events, extremes, get_peaks
from pydantic import BaseModel, FilePath

from hydroflows._typing import ListOfFloat
from hydroflows.methods.method import Method
from hydroflows.workflows.events import EventCatalog

__all__ = ["WflowDesignHydro"]


class Input(BaseModel):
    """Input parameters."""

    time_series_nc: FilePath


class Output(BaseModel):
    """Output parameters."""

    event_catalog: Path


class Params(BaseModel):
    """Parameters."""

    # parameters for the get_peaks function
    ev_type: str = "BM"
    min_dist_days: int = 7
    qthresh: float = 0.95
    min_sample_perc: int = 80
    index_dim: str = "Q_gauges"
    time_dim: str = "time"
    t0: str = "2020-01-01"

    # return periods of interest
    rps: ListOfFloat = [1, 2, 5, 10, 20, 50, 100]

    plot_fig: bool = True

    # duration for hydrograph
    wdw_size_days: int = 6


class WflowDesignHydro(Method):
    """Rule for creating fluvial design hydrograph."""

    name: str = "wflow_design_hydro"
    params: Params = Params()  # optional parameters
    input: Input
    output: Output

    def run(self):
        """Run the Wflow design hydrograph method."""
        # read the provided wflow time series
        da = xr.open_dataarray(self.input.time_series_nc)
        time_dim = self.params.time_dim
        index_dim = self.params.index_dim
        # check if dims in da
        for dim in [time_dim, index_dim]:
            if dim not in da.dims:
                raise ValueError(
                    f"{dim} not a dimension in, {self.input.time_series_nc}"
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

        # hydrographs based on the 10 highest peaks
        da_q_hydrograph = design_events.get_peak_hydrographs(
            da,
            da_peaks,
            wdw_size=wdw_size,
            n_peaks=10,
        ).transpose(time_dim, "peak", index_dim)

        # calculate the mean design hydrograph per rp
        q_hydrograph = da_q_hydrograph.mean("peak") * da_rps

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
        for i, rp in enumerate(q_hydrograph.rps.values):
            # save q_rp as csv files
            name = f"q_event{int(i+1):02d}"
            events_fn = Path(root, f"{name}.csv")
            q_hydrograph.sel(rps=rp).to_pandas().round(2).to_csv(events_fn)

            event = {
                "name": name,
                "forcings": [{"type": "discharge", "path": f"{name}.csv"}],
                "probability": 1 / rp,
            }
            events_list.append(event)

        # make a data catalog
        event_catalog = EventCatalog(
            root=root,
            events=events_list,
        )
        event_catalog.to_yaml(self.output.event_catalog)
