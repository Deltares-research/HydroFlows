"""Utils for coastal methods."""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import xarray as xr
from shapely import Point


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


def clip_coastrp(coast_rp: xr.DataArray, region: gpd.GeoDataFrame) -> xr.DataArray:
    """Clip COAST-RP to given region.

    Parameters
    ----------
    coast_rp : xr.DataArray
        DataArray containing COAST-RP data with lat,lon coords.
    region : gpd.GeoDataFrame
        Region GeoDataFrame

    Returns
    -------
    xr.DataArray
        Clipped COAST-RP DataArray
    """
    points = []
    for station in coast_rp.stations:
        point = Point(
            coast_rp.sel(stations=station).lon.values,
            coast_rp.sel(stations=station).lat.values,
        )
        if region.contains(point)[0]:
            points.append(station)
    return coast_rp.sel(stations=points)
