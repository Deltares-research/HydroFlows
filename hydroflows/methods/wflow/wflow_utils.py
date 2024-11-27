"""Utility functions for the wflow model."""
import datetime
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import tomli
import xarray as xr
from dateutil.relativedelta import relativedelta
from matplotlib import colors
from matplotlib.axes import Axes
from matplotlib.figure import Figure

# Note: should be moved to hydromt_wflow
__all__ = ["plot_forcing", "plot_basemap"]

# plot axes labels
_ATTRS = {
    "precip": {
        "standard_name": "precipitation",
        "unit": "mm.day-1",
        "color": "darkblue",
    },
    "pet": {
        "standard_name": "potential evapotranspiration",
        "unit": "mm.day-1",
        "color": "purple",
    },
    "temp": {"standard_name": "temperature", "unit": "degree C", "color": "orange"},
}


def shift_time(
    time: str,
    delta: int | float,
    format: str = "%Y-%m-%dT%H:%M:%S",
    units: str = "hours",
):
    """_summary_."""
    time_obj = datetime.datetime.strptime(time, format)
    if units in ["months", "years"]:
        dt = relativedelta(**{units: delta})
    else:
        dt = datetime.timedelta(**{units: delta})
    # Add the time
    time_obj = time_obj + dt

    # return back to a string
    return time_obj.strftime(format=format)


def plot_forcing(mod, dvars=None):
    """Plot the forcing data of a model instance."""
    if dvars is None:
        dvars = list(mod.data_vars)
    if not mod.forcing or not all([d in mod.forcing for d in dvars]):
        raise ValueError("No or incomplete forcing data found in model instance.")

    ds_forcing = xr.merge([mod.forcing[d] for d in dvars])
    n = len(ds_forcing.data_vars)
    kwargs0 = dict(sharex=True, figsize=(6, n * 3))

    fig, axes = plt.subplots(n, 1, **kwargs0)
    axes = [axes] if n == 1 else axes
    for i, name in enumerate(ds_forcing.data_vars):
        df = ds_forcing[name].squeeze().to_series()
        attrs = _ATTRS[name]
        longname = attrs.get("standard_name", "")
        unit = attrs.get("unit", "")
        if name == "precip" and df.index.size < 100:
            # for large time series, this is too slow
            axes[i].bar(df.index, df.values, facecolor=attrs["color"])
        else:
            df.plot.line(ax=axes[i], x="time", color=attrs["color"])
        axes[i].set_title(longname)
        axes[i].set_ylabel(f"{longname}\n[{unit}]")
    return fig


def plot_basemap(
    mod, figsize=(10, 8), zoom_level=10, shaded=False, fn_out: Path | None = None
) -> tuple[Figure, Axes]:
    """Plot a basemap of the model instance.

    Parameters
    ----------
    mod : hydromt.models.WflowModel
        The wflow model instance.
    figsize : tuple, optional
        Figure size, by default (10, 8)
    zoom_level : int, optional
        Zoom level for the background image, by default 10
    """
    # we assume the model maps are in the geographic CRS EPSG:4326
    proj = ccrs.PlateCarree()

    # read and mask the model elevation
    maps = ["wflow_dem", "wflow_subcatch", "wflow_river"]
    if not np.isin(maps, list(mod.grid.data_vars.keys())).all():
        raise ValueError("Model instance does not contain required maps data.")
    da = mod.grid["wflow_dem"].raster.mask_nodata()
    da = da.where(mod.grid["wflow_subcatch"] > 0)
    da.attrs.update(long_name="elevation", units="m")
    # read/derive river geometries
    gdf_riv = mod.rivers
    # read/derive model basin boundary
    mod.grid["wflow_subcatch"] = mod.grid["wflow_subcatch"].astype(np.int32)
    mod.grid["wflow_subcatch"].raster.set_nodata(0)
    gdf_bas = mod.basins

    # initialize image with geoaxes
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(projection=proj)
    bbox = da.raster.box.to_crs(3857).buffer(5e3).to_crs(da.raster.crs).total_bounds
    extent = np.array(bbox)[[0, 2, 1, 3]]
    ax.set_extent(extent, crs=proj)

    # add sat background image
    ax.add_image(cimgt.QuadtreeTiles(), zoom_level, alpha=0.5)

    ## plot elevation\
    # create nice colormap
    vmin, vmax = da.quantile([0.0, 0.98]).compute()
    c_dem = plt.cm.terrain(np.linspace(0.25, 1, 256))
    cmap = colors.LinearSegmentedColormap.from_list("dem", c_dem)
    norm = colors.Normalize(vmin=vmin, vmax=vmax)
    kwargs = dict(cmap=cmap, norm=norm)
    # plot 'normal' elevation
    da.plot(
        transform=proj,
        ax=ax,
        zorder=1,
        cbar_kwargs=dict(aspect=30, shrink=0.8),
        **kwargs,
    )
    # plot elevation with shades
    if shaded:
        ls = colors.LightSource(azdeg=315, altdeg=45)
        dx, dy = da.raster.res
        _rgb = ls.shade(
            da.fillna(0).values,
            norm=kwargs["norm"],
            cmap=kwargs["cmap"],
            blend_mode="soft",
            dx=dx,
            dy=dy,
            vert_exag=200,
        )
        rgb = xr.DataArray(dims=("y", "x", "rgb"), data=_rgb, coords=da.raster.coords)
        rgb = xr.where(np.isnan(da), np.nan, rgb)
        rgb.plot.imshow(transform=proj, ax=ax, zorder=2)

    # plot rivers with increasing width with stream order
    if gdf_riv is not None:
        gdf_riv.plot(
            ax=ax,
            linewidth=gdf_riv["strord"] / gdf_riv["strord"].max() * 1 + 0.5,
            color="blue",
            zorder=3,
            label="river",
        )
    # plot the basin boundary
    if gdf_bas is not None:
        gdf_bas.boundary.plot(ax=ax, color="k", linewidth=0.3)
    # plot various vector layers if present
    gauges = [name for name in mod.geoms if name.startswith("gauges")]
    for name in gauges:
        mod.geoms[name].plot(
            ax=ax, marker="d", markersize=25, facecolor="red", zorder=5, label=name
        )
    patches = []  # manual patches for legend, see https://github.com/geopandas/geopandas/issues/660
    if "lakes" in mod.geoms:
        kwargs = dict(
            facecolor="lightblue", edgecolor="black", linewidth=1, label="lakes"
        )
        mod.geoms["lakes"].plot(ax=ax, zorder=4, **kwargs)
        patches.append(mpatches.Patch(**kwargs))
    if "reservoirs" in mod.geoms:
        kwargs = dict(
            facecolor="white", edgecolor="black", linewidth=1, label="reservoirs"
        )
        mod.geoms["reservoirs"].plot(ax=ax, zorder=4, **kwargs)
        patches.append(mpatches.Patch(**kwargs))
    if "glaciers" in mod.geoms:
        kwargs = dict(facecolor="grey", edgecolor="grey", linewidth=1, label="glaciers")
        mod.geoms["glaciers"].plot(ax=ax, zorder=4, **kwargs)
        patches.append(mpatches.Patch(**kwargs))

    ax.xaxis.set_visible(True)
    ax.yaxis.set_visible(True)
    ax.set_ylabel("latitude [degree north]")
    ax.set_xlabel("longitude [degree east]")
    _ = ax.set_title("wflow base map")
    _ = ax.legend(
        handles=[*ax.get_legend_handles_labels()[0], *patches],
        title="Legend",
        loc="lower right",
        frameon=True,
        framealpha=0.7,
        edgecolor="k",
        facecolor="white",
    )
    if fn_out is not None:
        if not Path(fn_out).is_absolute():
            fn_out = Path(mod.root) / "figs" / fn_out
        if not Path(fn_out).parent.exists():
            Path(fn_out).parent.mkdir(parents=True)
        plt.savefig(fn_out, dpi=300, bbox_inches="tight")
    return fig, ax


def get_wflow_basemodel_root(wflow_toml: Path) -> Path:
    """Get folder with WFLOW static files from input.path_static config.

    Parameters
    ----------
    wflow_toml : Path
        Path to event wflow toml file.

    Returns
    -------
    Path
        Path to parent directory with static files.
    """
    with open(wflow_toml, "rb") as f:
        config = tomli.load(f)

    static_path = config["input"]["path_static"]

    n = 0
    n = max(n, static_path.count("../"))

    return wflow_toml.parents[n]
