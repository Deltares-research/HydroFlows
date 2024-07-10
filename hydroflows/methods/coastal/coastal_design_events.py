"""Create hydrographs for coastal waterlevels."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import xarray as xr
from hydromt.stats import get_peak_hydrographs, get_peaks
from pydantic import BaseModel

from hydroflows.methods.method import Method
from hydroflows.workflows.events import EventCatalog


class Input(BaseModel):
    """Input parameters for the :py:class:`CoastalDesginEvents` method."""

    surge_timeseries: Path
    """Path to surge timeseries data."""

    tide_timeseries: Path
    """Path to tides timeseries data."""

    rps_nc: Path
    """Path to return periods and values dataset."""


class Output(BaseModel):
    """Output parameters for the :py:class:`CoastalDesginEvents` method."""

    event_catalog: Path
    """Path to event catalog containing derived events"""


class Params(BaseModel):
    """Params for the :py:class:`CoastalDesginEvents` method."""

    ndays: int = 6
    """Duration of derived events in days."""

    t0: str = "2020-01-01"
    """Arbitrary time of event peak."""

    plot_fig: bool = True
    """Make hydrograph plots"""


class CoastalDesignEvents(Method):
    """Method for deriving extreme event waterlevels from tide and surge timeseries.

    Utilizes :py:class:`Input <hydroflows.methods.coastal.coastal_design_events.Input>`,
    :py:class:`Output <hydroflows.methods.coastal.coastal_design_events.Output>`, and
    :py:class:`Params <hydroflows.methods.coastal.coastal_design_events.Params>` for method inputs, outputs and params.

    See Also
    --------
    :py:function:`hydroflows.methods.coastal.coastal_design_events.plot_hydrographs`
    """

    name: str = "coastal_design_events"
    input: Input
    output: Output
    params: Params = Params()

    def run(self):
        """Run CoastalDesignEvents method."""
        da_surge = xr.open_dataarray(self.input.surge_timeseries)
        da_tide = xr.open_dataarray(self.input.tide_timeseries)
        da_rps = xr.open_dataset(self.input.rps_nc)

        da_mhws_peaks = get_peaks(da_tide, "BM", min_dist=6 * 24 * 10, period="29.5D")
        tide_hydrographs = (
            get_peak_hydrographs(
                da_tide,
                da_mhws_peaks,
                wdw_size=int(6 * 24 * self.params.ndays),
                normalize=False,
            )
            .transpose("time", "peak", ...)
            .mean("peak")
        )

        da_surge_peaks = get_peaks(da_surge, "BM", min_dist=6 * 24 * 10)
        surge_hydrographs = (
            get_peak_hydrographs(
                da_surge,
                da_surge_peaks,
                wdw_size=int(6 * 24 * self.params.ndays),
                normalize=False,
            )
            .transpose("time", "peak", ...)
            .mean("peak")
        )

        nontidal_rp = da_rps["return_values"] - tide_hydrographs
        h_hydrograph = tide_hydrographs + surge_hydrographs * nontidal_rp
        h_hydrograph = h_hydrograph.assign_coords(
            time=pd.to_datetime(self.params.t0)
            + pd.to_timedelta(10 * h_hydrograph.time, unit="min")
        )
        h_hydrograph = h_hydrograph.reset_coords(drop=True)

        root = self.output.event_catalog.parent
        root.mkdir(parents=True, exist_ok=True)

        events_list = []
        for i, rp in enumerate(h_hydrograph.rps):
            event_fn = Path(root, f"h_event{int(i+1):02d}.csv")
            h_hydrograph.sel(rps=rp).to_pandas().to_csv(event_fn)
            event = {
                "name": f"h_event{int(i+1):02d}",
                "forcings": [{"type": "water_level", "path": f"h_event{int(i+1):02d}"}],
                "probability": 1 / rp,
            }
            events_list.append(event)

        event_catalog = EventCatalog(
            root=root,
            events=events_list,
        )
        event_catalog.to_yaml(self.output.event_catalog)

        if self.params.plot_fig:
            savefolder = Path(root, "figs")
            if not savefolder.exists():
                savefolder.mkdir(parents=True)
            plot_hydrographs(h_hydrograph, savefolder / "waterlevel_hydrographs.png")


def plot_hydrographs(
    da_hydrograph: xr.DataArray,
    savepath: Path,
) -> None:
    """Plot and save hydrographs.

    Parameters
    ----------
    da_hydrograph : xr.DataArray
        DataArray containing hydrographs. Has rps and time dimensions.
    savepath : Path
        Save path for figure.
    """
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot()

    da_hydrograph.rename({"rps": "Return Period [year]"}).plot.line(ax=ax, x="time")
    ax.set_xlabel("Time")
    ax.set_ylabel("Waterlevel [m+MSL]")
    ax.set_title("Coastal Waterlevel Hydrographs")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(savepath, dpi=150, bbox_inches="tight")
