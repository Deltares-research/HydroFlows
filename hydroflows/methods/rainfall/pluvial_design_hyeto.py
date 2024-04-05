"""Pluvial design hyetograph method."""
from typing import List

import numpy as np
import pandas as pd
import xarray as xr
from functions import eva_idf, get_hyetograph
from hydromt.stats import extremes, get_peaks
from pydantic import BaseModel, FilePath

from ..method import Method

__all__ = ["PluvialDesignHyeto"]

class Input(BaseModel):
    """Input parameters."""

    time_series_nc: FilePath

class Output(BaseModel):
    """Output parameters."""


class Params(BaseModel):
    """Parameters."""

    # durations for IDF
    durations: List[int] = [1, 2, 3, 6, 12, 24, 36, 48]

    min_dist_days: int = 0
    ev_type: str = "BM"
    qthresh: float = 0.95
    min_sample_perc: int = 80
    time_dim: str = 'time'

    # return periods of interest
    rps: np.ndarray = np.array([1.01, 2, 5, 10, 20, 50, 100])

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

        dt = pd.Timedelta(da[time_dim].values[1] - da[time_dim].values[0])
        min_dist = int(pd.Timedelta(self.params.min_dist_days, 'd') / dt)

        # sample size per year
        min_sample_size = pd.Timedelta(1, 'A') / dt * self.params.min_sample_perc

        # specify the setting for extracting peaks
        kwargs = {
            "POT": dict(min_dist=min_dist,
                        qthresh=self.params.qthresh,
                        period='year'),
            "BM": dict(min_dist=min_dist,
                       period='year',
                       min_sample_size=min_sample_size)
        }[self.params.ev_type]

        # derive the peak
        da_peaks = get_peaks(da, ev_type=self.params.ev_type,
                             time_dim=time_dim, **kwargs)

        # specify and fit an EV distribution
        da_params = extremes.fit_extremes(da_peaks, ev_type=self.params.ev_type)
        da_params.load()

        # calculate return values for specified rps/params
        da_rps = extremes.get_return_value(da_params, rps=self.params.rps).load()
        da_rps = da_rps.assign_coords(rps=np.round(self.params.rps).astype(int))

        # specify the max event duration
        event_duration = self.params.durations[-1]

        # fit distribution per duration
        ds_idf = eva_idf(
                da,
                ev_type=self.params.ev_type,
                durations=self.params.durations,
                rps=self.params.rps,
        )

        ds_idf = ds_idf.assign_coords(rps=np.round(self.params.rps).astype(int))

        # Get design events hyetogrpah for each return period
        get_hyetograph(
            ds_idf["return_values"], dt=1, length=event_duration
        )
