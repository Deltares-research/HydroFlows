"""Derive tide and surge from waterlevel timeseries based on a tidal analysis."""

from pathlib import Path

import hatyan
import pandas as pd
import xarray as xr
from dateutil.relativedelta import relativedelta

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["CoastalTidalAnalysis", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`CoastalTidalAnalysis` method."""

    waterlevel_nc: Path
    """Path to water level time series in NetCDF format whici is used to derive tide and surge."""


class Output(Parameters):
    """Output parameters for the :py:class:`CoastalTidalAnalysis` method."""

    surge_timeseries: Path
    """Path to output surge timeseries."""

    tide_timeseries: Path
    """Path to output tide timeseries."""


class Params(Parameters):
    """Params for the :py:class:`CoastalTidalAnalysis` method."""

    data_root: Path = Path("data/input")

    plot_fig: bool = True
    """Make tidal component and timeseries plots.
    Note: the timeseries difference plot is -1*surge timeseries"""


class CoastalTidalAnalysis(Method):
    """Derive tide and surge from waterlevel timeseries based on a tidal analysis.

    Implements hatyan package to do tidal analysis. Uses 94 tidal constituents to estimate tidal signal.

    Parameters
    ----------
    waterlevel_timeseries : Path
        Path to waterlevel timeseries to derive tide and surge from.
    data_root : Path, optional
        Folder root where output is stored, by default "data/input/forcing/waterlevel"

    See Also
    --------
    :py:class:`CoastalTidalAnalysis Input <hydroflows.methods.coastal.coastal_tidal_analysis.Input>`
    :py:class:`CoastalTidalAnalysis Output <hydroflows.methods.coastal.coastal_tidal_analysis.Output>`
    :py:class:`CoastalTidalAnalysis Params <hydroflows.methods.coastal.coastal_tidal_analysis.Params>`
    """

    name: str = "coastal_tidal_analysis"

    _test_kwargs = {
        "waterlevel_nc": Path("waterlevel.nc"),
    }

    def __init__(
        self,
        waterlevel_nc: Path,
        data_root: Path = Path("data/input"),
        **params,
    ) -> None:
        self.input: Input = Input(waterlevel_nc=waterlevel_nc)
        self.params: Params = Params(data_root=data_root, **params)

        surge_out = self.params.data_root / "surge_timeseries.nc"
        tide_out = self.params.data_root / "tide_timeseries.nc"
        self.output: Output = Output(
            tide_timeseries=tide_out, surge_timeseries=surge_out
        )

    def _run(self) -> None:
        """Run CoastalTidalAnalysis method."""
        # Open waterlevel data
        h = xr.open_dataarray(self.input.waterlevel_nc)
        h = h.squeeze()
        ts = pd.DataFrame({"values": h.to_series()})

        time_slice = slice(
            h.time[0].values,
            h.time.values[-1],
            pd.Timedelta(h.time.diff(dim="time")[0].values),
        )

        # Get list of tidal components
        const_list = hatyan.get_const_list_hatyan("year")

        # Get amplitude, phase of tidal components
        comp_mean = hatyan.analysis(
            ts=ts,
            const_list=const_list,
            nodalfactors=True,
            return_allperiods=False,
            fu_alltimes=True,
            analysis_perperiod="Y",
        )
        # Get tidal timeseries
        ts_pred = hatyan.prediction(comp=comp_mean, times=time_slice)
        # Get surge timeseries
        ts_surge = ts - ts_pred

        if self.params.plot_fig:
            savefolder = Path(self.output.tide_timeseries.parent, "figs")
            if not savefolder.exists():
                savefolder.mkdir(parents=True)

            plot_tide_components(comp_mean, savefolder / "tidal_components.png")
            plot_timeseries(ts, ts_pred, savefolder / "tide_timeseries.png")

        t = xr.zeros_like(h)
        t.data = ts_pred.values.squeeze()
        t = t.rename("tide")

        s = xr.zeros_like(h)
        s.data = ts_surge.values.squeeze()
        s = s.rename("surge")

        t.to_netcdf(self.output.tide_timeseries)
        s.to_netcdf(self.output.surge_timeseries)


def plot_tide_components(comp, savepath):
    fig, (ax1, ax2) = hatyan.plot_components(comp=comp)
    fig.savefig(savepath, dpi=150, bbox_inches="tight")


def plot_timeseries(ts, ts_pred, savepath):
    fig, (ax1, ax2) = hatyan.plot_timeseries(ts=ts_pred, ts_validation=ts)
    lower, upper = (ts - ts_pred).min().values, (ts - ts_pred).max().values
    ax2.set_ylim(lower, upper)
    ax1.set_xlim(ts_pred.index[-1], ts_pred.index[-1] - relativedelta(years=1))
    fig.savefig(savepath, dpi=150, bbox_inches="tight")
