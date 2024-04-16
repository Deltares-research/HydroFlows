"""Pluvial design hyetograph method."""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from pydantic import BaseModel, FilePath

from hydroflows._typing import ListOfInt
from hydroflows.methods.method import Method
from hydroflows.methods.rainfall.functions import eva_idf, get_hyetograph
from hydroflows.workflows.events import EventCatalog

__all__ = ["PluvialDesignHyeto"]

class Input(BaseModel):
    """Input parameters."""

    time_series_nc: FilePath

class Output(BaseModel):
    """Output parameters."""

    event_catalog: Path

class Params(BaseModel):
    """Parameters."""

    # durations for IDF
    durations: ListOfInt = [1, 2, 3, 6, 12, 24, 36, 48]

    min_dist_days: int = 0
    ev_type: str = "BM"
    qthresh: float = 0.95
    min_sample_perc: int = 80
    time_dim: str = 'time'

    # return periods of interest
    rps: ListOfInt= [1, 2, 5, 10, 20, 50, 100]

    plot_fig: bool = True

class PluvialDesignHyeto(Method):
    """Rule for creating pluvial design hyetograph."""

    name: str = "pluvial_design_hyeto"
    params: Params = Params() # optional parameters
    input: Input
    output: Output

    def run(self):
        """Run the Pluvial design hyetograph method."""
        da = xr.open_dataarray(self.input.time_series_nc)
        time_dim = self.params.time_dim
        if da.ndim > 1 or time_dim not in da.dims:
            raise ValueError()


        dt = pd.Timedelta(da[time_dim].values[1] - da[time_dim].values[0])
        int(pd.Timedelta(self.params.min_dist_days, 'd') / dt)

        # sample size per year
        min_sample_size = pd.Timedelta(1, 'A') / dt * self.params.min_sample_perc

        # convert rps list to an array with min value to avoid infs
        rps= np.max(1.001, self.params.rps)
        # specify the max event duration
        event_duration = self.params.durations[-1]

        # fit distribution per duration
        ds_idf = eva_idf(
            da,
            ev_type=self.params.ev_type,
            durations=self.params.durations,
            rps=rps,
            qthresh=self.params.qthresh,
            min_sample_size=min_sample_size
        )

        ds_idf = ds_idf.assign_coords(rps=np.round(rps).astype(int))

        # Get design events hyetogrpah for each return period
        p_hyetograph = get_hyetograph(
            ds_idf["return_values"], dt=1, length=event_duration
        )

        # random starting time
        dt0 = pd.to_datetime("2020-01-01")
        time_delta = pd.to_timedelta(p_hyetograph['time'], unit='h').round('10min')
        p_hyetograph['time'] = dt0 + time_delta
        p_hyetograph = p_hyetograph.reset_coords(drop=True)

        root = self.output.event_catalog.parent

        events_list = []
        for rp in p_hyetograph.rps.values:
            # save p_rp as csv files
            events_fn = os.path.join(root, f"p_rp{int(rp):03d}.csv")
            p_hyetograph.sel(rps=rp).to_pandas().round(2).to_csv(events_fn)

            event = {
                "name": f"p_rp{int(rp):03d}",
                "forcings": [{"type": "rainfall", "path": f"p_rp{int(rp):03d}.csv"}],
                "probability": 1/rp
             }
            events_list.append(event)

        # make a data catalog
        event_catalog = EventCatalog(
           root=root,
           events=events_list,
        )

        event_catalog.to_yaml(
            self.output.event_catalog)

        # save plots
        if self.params.plot_fig:
            # create a folder to save the figs
            fn_plots = os.path.join(root, 'figs')

            if not os.path.exists(fn_plots):
                os.makedirs(fn_plots)

            # Plot IDF curves
            fig, ax = plt.subplots(1, 1, figsize=(8, 4), sharex=True)
            df = ds_idf["return_values"].rename(
                {"rps": "Return period\n[year]"}
                ).to_pandas()
            df.plot(ax=ax)
            ax.set_ylabel("rainfall intensity [mm/hour]")
            ax.set_xlabel("event duration [hour]")
            ax.set_title("Rainfall IDF curves")
            ax.grid(True)
            fig.tight_layout()
            fig.savefig(os.path.join(
                fn_plots, "rainfall_idf.png"), dpi=150, bbox_inches="tight")

            # Plot hyetographs
            fig, ax = plt.subplots(1, 1, figsize=(8, 4), sharex=True)
            p_hyetograph.rename({"rps": "Return period\n[year]"}).plot.step(
                x="time", where="mid", ax=ax,
            )
            ax.set_ylabel("rainfall intensity [mm/hour]")
            ax.set_xlabel("time [hour]")
            ax.set_title("Rainfall hyetographs")
            ax.grid(True)
            fig.tight_layout()
            fig.savefig(os.path.join(
                fn_plots, "rainfall_hyetographs.png"), dpi=150, bbox_inches="tight")
