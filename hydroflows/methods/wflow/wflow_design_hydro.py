"""Wflow design hydrograph method."""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from hydromt.stats import design_events, extremes, get_peaks
from pydantic import BaseModel, FilePath

from ..method import Method

__all__ = ["WflowDesignHydro"]

class Input(BaseModel):
    """Input parameters."""

    time_series_nc: FilePath

class Output(BaseModel):
    """Output parameters."""

    design_hydrograph: Path

class Params(BaseModel):
    """Parameters."""

    #parameters for the get_peaks function
    ev_type: str = "BM"
    min_dist_days: int = 7
    qthresh: float = 0.95
    min_sample_perc: int = 80
    index_dim: str = 'Q_gauges'
    time_dim: str = 'time'

    #return periods of interest
    rps: np.ndarray = np.array([1.01, 2, 5, 10, 20, 50, 100])

    plot_fig: bool = False

    #duration for hydrograph
    ndays: int = 6

class WflowDesignHydro(Method):
    """Rule for creating fluvial design hydrograph."""

    name: str = "wflow_design_hydro"
    params: Params = Params() # optional parameters
    input: Input
    output: Output

    def run(self):
        """Run the Wflow design hydrograph method."""
        #read the provided wflow time series
        da = xr.open_dataarray(self.input.time_series_nc)
        time_dim = self.params.time_dim
        index_dim = self.params.index_dim
        # check if dims in da
        for dim in [time_dim, index_dim]:
            if dim not in da.dims:
                raise ValueError(
                    f'{dim} not a dimension in, {self.input.time_series_nc}')

        dt = pd.Timedelta(da[time_dim].values[1] - da[time_dim].values[0])
        min_dist = int(pd.Timedelta(self.params.min_dist_days, 'd') / dt)

        # sample size per year
        min_sample_size = pd.Timedelta(1, 'A') / dt * self.params.min_sample_perc

        #specify the setting for extracting peaks
        kwargs = {
            "POT": dict(min_dist=min_dist,
                        qthresh=self.params.qthresh,
                        period='year'),
            "BM": dict(min_dist=min_dist,
                       period='year',
                       min_sample_size=min_sample_size)
        }[self.params.ev_type]

        #derive the peak
        da_peaks = get_peaks(da, ev_type=self.params.ev_type,
                             time_dim=time_dim, **kwargs)

        #TODO reduce da_peaks to n year samples in case of POT

        #specify and fit an EV distribution
        da_params = extremes.fit_extremes(da_peaks, ev_type=self.params.ev_type)
        da_params.load()

        #calculate return values for specified rps/params
        da_rps = extremes.get_return_value(da_params, rps=self.params.rps).load()
        da_rps = da_rps.assign_coords(rps=np.round(self.params.rps).astype(int))

        da_q_hydrograph = design_events.get_peak_hydrographs(
                            da,
                            da_peaks,
                            wdw_size=self.params.ndays,
                            ).transpose(time_dim, 'peak', index_dim)

        q_hydrograph = da_q_hydrograph.mean('peak') * da_rps

        q_hydrograph.to_netcdf(self.output.design_hydrograph)

        #save plots with fitted distributions
        if self.params.plot_fig == True:

            #create a folder to save the figs
            root = self.output.design_hydrograph.parent
            plots_folder = os.path.join(root, 'plots_eva')

            if not os.path.exists(plots_folder):
                os.makedirs(plots_folder)

            #loop through all the stations and save fig
            for station in da[index_dim].values:
                _, ax = plt.subplots(1, 1, figsize=(7, 5))

                extremes_rate = da_peaks.sel({index_dim: station}).extremes_rate.item()
                dist = da_params.sel({index_dim: station}).distribution.item()

                extremes.plot_return_values(
                        da_peaks.sel({index_dim: station}),
                        da_params.sel({index_dim: station}),
                        dist,
                        color="k",
                        nsample=1000,
                        rps=self.params.rps,
                        extremes_rate=extremes_rate,
                        ax=ax,)

                ax.set_title(f"Station {station}")
                ax.set_ylabel(R"Discharge [m$^{3}$ s$^{-1}$]")
                ax.set_xlabel("Return period [years]")

                station_fig_path = os.path.join(plots_folder, f"{station}.png")

                plt.savefig(station_fig_path, dpi=300, bbox_inches="tight")
