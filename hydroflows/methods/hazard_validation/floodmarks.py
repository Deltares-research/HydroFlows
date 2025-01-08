"""Validate simulated hazard maps using floodmarks method."""

import logging
from pathlib import Path
from typing import Literal, Union

import geopandas as gpd
import hydromt
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from pydantic import PositiveInt
from shapely.geometry import Point

from hydroflows._typing import ListOfFloat, TupleOfInt
from hydroflows.utils.units import convert_to_meters
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

logger = logging.getLogger(__name__)


class Input(Parameters):
    """Input parameters for the :py:class:`FloodmarksValidation` method."""

    floodmarks_geom: Path
    """
    The file path to a geometry file (e.g. shapefile, GeoJSON, GeoPackage etc.) containing the locations of
    floodmarks as points. This file should include an attribute/property representing the
    corresponding water levels at each location.
    """

    flood_hazard_map: Path
    """
    The file path to the flood hazard map to be used for validation, provided in TIFF format.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`FloodmarksValidation` method."""

    validation_scores_geom: Path
    """The path to the geometry file with the derived validation scores."""

    validation_scores_csv: Path
    """The path to the CSV file with the derived validation scores."""


class Params(Parameters):
    """Parameters for :py:class:`FloodmarksValidation` method."""

    out_root: Path
    """Root folder to save the derived validation scores."""

    waterlevel_col: str
    """The column/attribute name representing the observed water level in the input floodmarks geometry file,
    as provided in the :py:class:`Input` class."""

    waterlevel_unit: Literal["m", "cm", "mm", "ft", "in"]
    """The unit (length) of the observed floodmarks in the input geometry file,
    as provided in the :py:class:`Input` class. Valid options are 'm' for meters
    , 'cm' for centimeters, "mm" for milimeters, "ft" for feet and "in" for inches."""

    filename: str = "validation_scores_floodmarks.csv"
    """The filename for the produced validation scores csv file."""

    plot_fig: bool = True
    """Determines whether to plot a figure, with the derived
    validation scores and the difference between observed and simulated
    values with color bins geographically."""

    # Plotting settings params
    bins: ListOfFloat = None
    """Custom bin edges for categorizing the the difference between
    observed and simulated values. If None (default), calculated based on `nbins`,
    `vmin` and `vmax`."""

    nbins: PositiveInt = 5
    """Number of bins for grouping the difference between observed and
    simulated values (for color mapping)."""

    vmin: Union[float, int] = None
    """Minimum value for the color scale. If None (default),
    the (rounded) minimum value of difference (observed - simulated) is used."""

    vmax: Union[float, int] = None
    """Maximum value for the color scale. If None (default),
    the maximum value of difference (observed - simulated) is used."""

    cmap: str = "bwr"
    """Colormap used for visualizing the difference (observed - simulated) values.
    Default is 'bwr' (blue-white-red)."""

    zoomlevel: str = "auto"
    """Zoomlevel, by default 'auto'. """

    figsize: TupleOfInt = (12, 7)
    """Figure size, by default (12,7)."""

    bmap: str = None
    """Background map souce name, by default None
    Default image tiles "sat", and "osm" are fetched from cartopy image tiles.
    If contextily is installed, xyzproviders tiles can be used as well."""

    region: Path = None
    """File path to the geometry file representing the area used for hazard simulation.
    This is only used for visualization pursposes. An example of this file could be a GeoJSON of the SFINCS region.
    """


class FloodmarksValidation(Method):
    """Rule for validating the derived flood hazard maps against floodmarks."""

    name: str = "floodmarks_validation"

    _test_kwargs = {
        "floodmarks_geom": Path("floodmarks.geojson"),
        "flood_hazard_map": Path("hazard_map_output.tif"),
        "waterlevel_col": "water_level_obs",
        "waterlevel_unit": "m",
    }

    def __init__(
        self,
        floodmarks_geom: Path,
        flood_hazard_map: Path,
        waterlevel_col: str,
        waterlevel_unit: Literal["m", "cm", "mm", "ft", "in"],
        out_root: Path = Path("data/validation"),
        **params,
    ):
        """Create and validate a FloodmarksValidation instance.

        Parameters
        ----------
        floodmarks_geom : Path
           Path to the geometry file (shapefile, GeoJSON or GeoPackage) with floodmark locations as
           points. The corresponding water levels are defined by the property specified
           in :py:attr:`waterlevel_col`.
        flood_hazard_map : Path
            The file path to the flood hazard map to be used for validation.
        scores_root : Path, optional
            The root folder to save the derived validation scores, by default "data/validation".
        waterlevel_col : Str
            The property name for the observed water levels in the floodmarks geometry file
        waterlevel_unit : Literal["m", "cm", "mm", "ft", "in"]
            Obsevred floodmarks unit. Valid options are 'm' for meters,
            'cm' for centimeters, 'ft' for feet and 'in' for inches .
        **params
            Additional parameters to pass to the FloodmarksValidation instance.

        See Also
        --------
        :py:class:`FloodmarksValidation Input <hydroflows.methods.validation.floodmarks_validation.Input>`
        :py:class:`FloodmarksValidation Output <hydroflows.methods.validation.floodmarks_validation.Output>`
        :py:class:`FloodmarksValidation Params <hydroflows.methods.validation.floodmarks_validation.Params>`
        """
        self.params: Params = Params(
            out_root=out_root,
            waterlevel_col=waterlevel_col,
            waterlevel_unit=waterlevel_unit,
            **params,
        )
        self.input: Input = Input(
            floodmarks_geom=floodmarks_geom,
            flood_hazard_map=flood_hazard_map,
        )
        self.output: Output = Output(
            validation_scores_geom=self.params.out_root
            / f"{self.input.floodmarks_geom.stem}_validation.gpkg",
            validation_scores_csv=self.params.out_root / self.params.filename,
        )

    def run(self):
        """Run the FloodmarksValidation method."""
        # Read the floodmarks and the region files
        gdf = gpd.read_file(self.input.floodmarks_geom)

        # Read the floodmap using HydroMT
        floodmap = hydromt.io.open_raster(self.input.flood_hazard_map)

        proj_crs = floodmap.raster.crs
        if not proj_crs.is_projected and proj_crs.to_epsg() is None:
            raise ValueError("Input hazard map needs to be georeferenced.")

        if gdf.crs != proj_crs:
            gdf = gdf.to_crs(proj_crs)

        # Include flood marks that fall within the flood_bounds_gdf
        gdf_in_region = gdf[gdf.geometry.within(floodmap.raster.box.union_all())]

        # Number of points inside (outside) the modeled region
        num_floodmarks_inside = len(gdf_in_region)
        num_floodmarks_outside = len(gdf) - num_floodmarks_inside

        if num_floodmarks_inside == 0:
            raise ValueError(
                "No floodmarks found within the modeled flood hazard map extents."
            )

        logging.info(
            f"Floodmarks inside the simulated region: {num_floodmarks_inside}/{num_floodmarks_outside}"
        )

        gdf_in_region.loc[:, "geometry"] = gdf_in_region["geometry"].apply(
            multipoint_to_point
        )

        # Sample the floodmap at the floodmark locs
        samples: xr.DataArray = floodmap.raster.sample(gdf_in_region)

        # Assign the modeled values to the gdf
        gdf_in_region.loc[:, "modeled_value"] = samples.fillna(0).values

        # Make sure the units are in meters
        gdf_in_region.loc[:, self.params.waterlevel_col] = gdf_in_region.loc[
            :, self.params.waterlevel_col
        ].apply(lambda x: convert_to_meters(x, self.params.waterlevel_unit))

        # Set 'is_flooded' to True if 'modeled_value' is greater than 0
        gdf_in_region.loc[:, "is_flooded"] = gdf_in_region["modeled_value"] > 0

        # Calculate the difference between observed and modeled values
        gdf_in_region.loc[:, "difference"] = (
            gdf_in_region[self.params.waterlevel_col] - gdf_in_region["modeled_value"]
        )

        # Calculate the abs. difference between observed and modeled values
        gdf_in_region.loc[:, "abs_difference"] = gdf_in_region.loc[
            :, "difference"
        ].abs()

        # Calculate RMSE and R²
        rmse = RMSE(
            gdf_in_region[self.params.waterlevel_col],
            gdf_in_region["modeled_value"],
        )

        r2 = R2(
            gdf_in_region[self.params.waterlevel_col].values,
            gdf_in_region["modeled_value"].values,
        )

        # Create a df with the scores and convert it to a csv
        metrics = {"rmse": [rmse], "r2": [r2]}
        df_metrics = pd.DataFrame(metrics)
        df_metrics.to_csv(self.output.validation_scores_csv, index=False)

        # Export the validated gdf
        gdf_in_region.to_file(self.output.validation_scores_geom, driver="GPKG")

        fig_root = self.output.validation_scores_geom.parent

        # save plot
        if self.params.plot_fig:
            # create a folder to save the figs
            plot_dir = Path(fig_root, "figs")
            plot_dir.mkdir(exist_ok=True)

            _plot_scores(
                scores_gdf=gdf_in_region,
                floodmap_ds=floodmap,
                region=self.params.region,
                nbins=self.params.nbins,
                rmse=rmse,
                r2=r2,
                path=Path(plot_dir, "validation_scores.png"),
                bins=self.params.bins,
                vmin=self.params.vmin,
                vmax=self.params.vmax,
                cmap=self.params.cmap,
                figsize=self.params.figsize,
                zoomlevel=self.params.zoomlevel,
                bmap=self.params.bmap,
            )


def multipoint_to_point(geometry):
    """Convert MultiPoint to Point.

    This function converts a `MultiPoint` geometry into a single `Point` by taking the first point in the collection.
    It ensures that if the input geometry is of type `MultiPoint`, it returns the first point in the geometry collection.
    If the geometry is not a `MultiPoint`, it returns the original geometry as it is.
    The function also supports 3D geometries (Point with z-coordinate).

    Parameters
    ----------
    geometry : shapely.geometry (e.g., Point, MultiPoint)
        The input geometry to be evaluated and converted if it is a MultiPoint.

    Returns
    -------
    shapely.geometry.Point or original geometry:
        - If the input geometry is a `MultiPoint`, the function returns a `Point` object corresponding to the first point
          in the collection (preserving the z-coordinate if present).
        - If the input geometry is not a `MultiPoint`, the original geometry is returned unchanged.
    """
    if geometry.geom_type == "MultiPoint":
        points = geometry.geoms
        if len(points) > 0:  # Check if there are points in the MultiPoint
            return Point(points[0].x, points[0].y, getattr(points[0], "z", 0))
    return geometry  # Return the original geometry if it's not a MultiPoint


def RMSE(actual, predicted):
    """
    Calculate Root Mean Squared Error (RMSE) between actual and predicted values.

    Parameters
    ----------
    actual (array-like): Array of actual values.
    predicted (array-like): Array of predicted values.

    Returns
    -------
    float: RMSE value.
    """
    actual = np.asarray(actual)
    predicted = np.asarray(predicted)

    mse = np.mean((actual - predicted) ** 2)
    rmse = np.sqrt(mse)
    return rmse


def R2(actual, predicted):
    """
    Calculate R-squared (R²) between actual and predicted values.

    Parameters
    ----------
    actual (array-like): Array of actual values.
    predicted (array-like): Array of predicted values.

    Returns
    -------
    float: R² value.
    """
    actual = np.asarray(actual)
    predicted = np.asarray(predicted)

    ss_total = np.sum((actual - np.mean(actual)) ** 2)
    ss_residual = np.sum((actual - predicted) ** 2)
    r2 = 1 - (ss_residual / ss_total)
    return r2


def _plot_scores(
    scores_gdf,
    floodmap_ds: xr.Dataset,
    region: Path,
    nbins,
    rmse,
    r2,
    path: Path,
    bins,
    vmin,
    vmax,
    cmap,
    figsize,
    zoomlevel,
    bmap,
) -> None:
    """Plot scores."""
    import cartopy.crs as ccrs
    import cartopy.io.img_tiles as cimgt

    try:
        import contextily as ctx

        has_cx = True
    except ImportError:
        has_cx = False

    # Set default values for vmin, vmax, cmap, and bins if not provided
    if vmin is None:
        vmin = np.floor(scores_gdf["difference"].min())
    if vmax is None:
        vmax = scores_gdf["difference"].max()
    if bins is None:
        bins = np.linspace(vmin, vmax, nbins + 1)

    bounds = floodmap_ds.raster.box.total_bounds
    extent = np.array(bounds)[[0, 2, 1, 3]]

    proj_crs = floodmap_ds.raster.crs
    proj_str = proj_crs.name
    if proj_crs.is_projected and proj_crs.to_epsg() is not None:
        crs = ccrs.epsg(floodmap_ds.raster.crs.to_epsg())
        unit = proj_crs.axis_info[0].unit_name
        unit = "m" if unit == "metre" else unit
        xlab, ylab = f"x [{unit}] - {proj_str}", f"y [{unit}]"
    elif proj_crs.is_geographic:
        crs = ccrs.PlateCarree()
        xlab, ylab = f"lon [deg] - {proj_str}", "lat [deg]"

    if zoomlevel == "auto":  # auto zoomlevel
        c = 2 * np.pi * 6378137  # Earth circumference
        lat = np.array(floodmap_ds.raster.transform_bounds(4326))[[1, 3]].mean()
        # max 4 x 4 tiles per image
        tile_size = max(bounds[2] - bounds[0], bounds[3] - bounds[1]) / 4
        if proj_crs.is_geographic:
            tile_size = tile_size * 111111
        zoomlevel = int(np.log2(c * abs(np.cos(lat)) / tile_size))
        # sensible range is 9 (large metropolitan area) - 16 (street)
        zoomlevel = min(16, max(9, zoomlevel))

    fig = plt.figure(figsize=figsize)
    ax = plt.subplot(projection=crs)
    ax.set_extent(extent, crs=crs)
    ax.set_title("Validation against flood marks", size=14)

    if bmap is not None:
        if zoomlevel == "auto":  # auto zoomlevel
            c = 2 * np.pi * 6378137  # Earth circumference
            lat = np.array(floodmap_ds.raster.transform_bounds(4326))[[1, 3]].mean()
            # max 4 x 4 tiles per image
            tile_size = max(bounds[2] - bounds[0], bounds[3] - bounds[1]) / 4
            if proj_crs.is_geographic:
                tile_size = tile_size * 111111
            zoomlevel = int(np.log2(c * abs(np.cos(lat)) / tile_size))
            # sensible range is 9 (large metropolitan area) - 16 (street)
            zoomlevel = min(16, max(9, zoomlevel))
        #  short names for cartopy image tiles
        bmap = {"sat": "QuadtreeTiles", "osm": "OSM"}.get(bmap, bmap)
        bmap_kwargs = {}
        if has_cx and bmap in list(ctx.providers.flatten()):
            bmap_kwargs = dict(zoom=zoomlevel, **bmap_kwargs)
            ctx.add_basemap(ax, crs=crs, source=bmap, **bmap_kwargs)
        elif hasattr(cimgt, bmap):
            bmap_img = getattr(cimgt, bmap)(**bmap_kwargs)
            ax.add_image(bmap_img, zoomlevel)
        else:
            err = f"Unknown background map: {bmap}"
            if not has_cx:
                err += " (note that contextily is not installed)"
            raise ValueError(err)

    # Add a region plot in case there is one
    if region is not None:
        region_gdf = gpd.read_file(region)
        region_gdf = region_gdf.to_crs(proj_crs)
        region_gdf.plot(
            ax=ax,
            color="grey",
            edgecolor="black",
            linewidth=2,
            alpha=0.3,
            label="Region",
        )

    cmap = plt.get_cmap(cmap)
    norm = mcolors.BoundaryNorm(bins, cmap.N)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])

    # Bin the 'difference' values and plot
    scores_gdf["binned"] = pd.cut(scores_gdf["difference"], bins=bins, labels=False)

    if len(scores_gdf[scores_gdf["binned"].isna() == True]) > 0:
        logger.warning(
            "There are flood mark difference (observed - modeled) values that fall outside "
            "the determined bin range and thus were excluded from the plot. "
            "Consider adjusting the plotting settings.",
            stacklevel=2,
        )

    for bin_val in range(len(bins) - 1):
        subset = scores_gdf[scores_gdf["binned"] == bin_val]
        # Skip plotting if the subset is empty
        if subset.empty:
            continue
        color = cmap(norm(bins[bin_val]))
        subset.plot(ax=ax, color=color, linewidth=1, edgecolor="black", markersize=100)

    # Add the color bar for the bins
    cbar = plt.colorbar(sm, ax=ax, shrink=0.75, orientation="vertical")
    cbar.set_label("Difference (Observed - Modeled) [m]")

    textstr = "\n".join(
        (
            f"Min Abs. Difference: {scores_gdf['abs_difference'].min():.2f} m",
            f"Max Abs. Difference: {scores_gdf['abs_difference'].max():.2f} m",
            f"RMSE: {rmse:.2f} m",
            f"R$^2$: {r2:.2f}",
        )
    )

    # matplotlib.patch.Patch properties
    props = dict(boxstyle="round", facecolor="white", alpha=0.8)

    ax.text(
        0.02,
        0.98,
        textstr,
        transform=ax.transAxes,
        fontsize=12,
        verticalalignment="top",
        bbox=props,
    )

    ax.xaxis.set_visible(True)
    ax.yaxis.set_visible(True)
    ax.set_ylabel(ylab)
    ax.set_xlabel(xlab)

    fig.savefig(path, dpi=150, bbox_inches="tight")
