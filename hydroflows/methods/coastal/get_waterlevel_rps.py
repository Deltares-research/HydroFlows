"""Get return periods from waterlevel timeseries."""

from pathlib import Path
from typing import Literal

import numpy as np
import xarray as xr
from hydromt.stats import fit_extremes, get_peaks, get_return_value
from pydantic import BaseModel

from hydroflows._typing import ListOfInt
from hydroflows.methods.method import Method

__all__ = ["GetWaterlevelRPS"]


class Input(BaseModel):
    """Input parameters for the :py:class:`GetWaterlevelRPS` method."""

    waterlevel_timeseries: Path
    """Path to total waterlevel timeseries"""


class Output(BaseModel):
    """Output parameters for the :py:class:`GetWaterlevelRPS` method."""

    rps_nc: Path
    """Path to return period and values dataset."""


class Params(BaseModel):
    """Params for the :py:class:`GetWaterlevelRPS` method."""

    rps: ListOfInt = [1, 2, 5, 10, 20, 50, 100]
    """List of return periods."""

    ev_type: Literal["BM", "POT"] = "BM"
    """Method for peak selection. BM for block maxima, POT for Peak over Threshold."""

    qthresh: float = 0.9
    """Quantile threshold to use with POT ev_type"""


class GetWaterlevelRPS(Method):
    """Method for deriving return values from total waterlevel timeseries for given return periods.

    See Also
    --------
    :py:function:`hydromt.stats.get_peaks`
    :py:function:`hydromt.stats.fit_extremes`
    :py:function:`hydromt.stats.get_return_values`
    """

    name: str = "get_waterlevel_rps"

    def __init__(
        self,
        waterlevel_timeseries: Path,
        data_root: Path = "data/input/forcing_data/waterlevel",
        **params,
    ) -> None:
        """Create and validate a GetWaterlevelRPS instance.

        Parameters
        ----------
        waterlevel_timeseries : Path
            Path to total waterlevel timeseries
        data_root : Path, optional
            The folder root where output is stored, by default "data/input/forcing_data/waterlevel"

        See Also
        --------
        :py:class:`Input <hydroflows.methods.coastal.get_waterlevel_rps.Input>`
        :py:class:`Input <hydroflows.methods.coastal.get_waterlevel_rps.Output>`
        :py:class:`Input <hydroflows.methods.coastal.get_waterlevel_rps.Params>`
        """
        self.input: Input = Input(waterlevel_timeseries=waterlevel_timeseries)
        self.params: Params = Params(**params)

        rps_fn = data_root / "waterlevel_rps.nc"
        self.output: Output = Output(rps_nc=rps_fn)

    def run(self) -> None:
        """Run GetWaterlevelRPS method."""
        da_h = xr.open_dataarray(self.input.waterlevel_timeseries)
        da_h_peaks = get_peaks(
            da_h,
            ev_type=self.params.ev_type,
            min_dist=6 * 24 * 10,
            qthresh=self.params.qthresh,
        )
        da_h_extremes = fit_extremes(da_h_peaks, ev_type=self.params.ev_type)
        h_rps = get_return_value(da_h_extremes, rps=np.array(self.params.rps))
        h_rps.to_netcdf(self.output.rps_nc)
