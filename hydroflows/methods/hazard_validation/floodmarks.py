"""Validate simulated hazard maps using floodmarks method."""

from pathlib import Path
from typing import Literal

import contextily as ctx
import geopandas as gpd
import hydromt
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from pydantic import PositiveInt
from shapely.geometry import Point

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


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

    region: Path
    """
    The file path to the geometry file representing the area used for hazard simulation.
    This is used to define flood marks outside the model domain.
    An example of this file could be a GeoJSON of the SFINCS region.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`FloodmarksValidation` method."""

    validation_scores_geom: Path
    """The path to the geometry file with the derived validation scores."""

    validation_scores_csv: Path
    """The path to the CSV file with the derived validation scores."""


class Params(Parameters):
    """Parameters for :py:class:`PluvialDesignEvents` method."""

    out_root: Path
    """Root folder to save the derived validation scores."""

    waterlevel_col: str
    """The column/attribute name representing the observed water level in the input floodmarks geometry file,
    as provided in the :py:class:`Input` class."""

    waterlevel_unit: Literal["m", "cm"] = "m"
    """The unit (length) of the observed floodmarks in the input geometry file,
    as provided in the :py:class:`Input` class. Valid options are 'm' for meters
    maxima or 'cm' for centimeters."""

    filename: str = "validation_scores_floodmarks.csv"
    """The filename for the produced validation scores csv file."""

    plot_fig: bool = True
    """Determines whether to plot a figure, with the derived
    validation scores and the difference between observed and simulated
    values with color bins geographically."""

    num_bins: PositiveInt = 5
    """The number of bins to divide the difference between observed and
    simulated values into color-coding in the plot, if the `plot_fig`
    parameter is set to True."""


class FloodmarksValidation(Method):
    """Rule for validating the derived flood hazard maps against floodmarks."""

    name: str = "floodmarks_validation"

    _test_kwargs = {
        "floodmarks_geom": Path("floodmarks.geojson"),
        "flood_hazard_map": Path("hazard_map_output.tif"),
        "region": Path("region.geojson"),
        "waterlevel_col": "water_level_obs",
    }

    def __init__(
        self,
        floodmarks_geom: Path,
        flood_hazard_map: Path,
        region: Path,
        waterlevel_col: str,
        waterlevel_unit: Literal["m", "cm"] = "m",
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
        region : Path
            Path to the geometry file defining the area for hazard simulation,
            such as the SFINCS region GeoJSON.
        flood_hazard_map : Path
            The file path to the flood hazard map to be used for validation.
        scores_root : Path, optional
            The root folder to save the derived validation scores, by default "data/validation".
        waterlevel_col : Str
            The property name for the observed water levels in the floodmarks geometry file
        waterlevel_unit : Literal["m", "cm"]
            Obsevred floodmarks unit. Valid options are 'm' (default)
            for meters or 'cm' centimeters.
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
            region=region,
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
        region = gpd.read_file(self.input.region)

        # Check CRS and reproject if necessary
        if gdf.crs != region.crs:
            gdf = gdf.to_crs(region.crs)

        # Ensure floodmarks fall within the region
        gdf_in_region = gdf[gdf.geometry.within(region.unary_union)]

        # Number of points inside (outside) the modeled region
        num_floodmarks_inside = len(gdf_in_region)
        num_floodmarks_outside = len(gdf) - num_floodmarks_inside

        if num_floodmarks_inside == 0:
            ValueError("No floodmarks found within the modeled region.")

        print(
            f"Floodmarks inside the simulated region: {num_floodmarks_inside}, Floodmarks outside: {num_floodmarks_outside}"
        )

        gdf_in_region["geometry"] = gdf_in_region["geometry"].apply(multipoint_to_point)

        # Read the floodmap
        floodmap = hydromt.io.open_raster(self.input.flood_hazard_map)

        # Sample the floodmap at the floodmark locs
        samples: xr.DataArray = floodmap.raster.sample(gdf_in_region)

        # Assign the modeled values to the gdf
        gdf_in_region.loc[:, "modeled_value"] = samples.fillna(0).values

        # If the observed water level is in cm convert it to m
        # TODO improve this part to allow different units
        if self.params.waterlevel_unit == "cm":
            gdf_in_region.loc[:, self.params.waterlevel_col] = (
                gdf_in_region.loc[:, self.params.waterlevel_col] / 100
            )

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
                region=region,
                num_bins=self.params.num_bins,
                rmse=rmse,
                r2=r2,
                path=Path(plot_dir, "validation_scores.png"),
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


def _plot_scores(scores_gdf, region, num_bins, rmse, r2, path: Path) -> None:
    """Plot scores."""
    # Get the min and max values and round them
    min_value = np.floor(scores_gdf["difference"].min())
    max_value = np.ceil(scores_gdf["difference"].max())

    # Define bins
    bins = np.linspace(min_value, max_value, num_bins + 1)

    fig, ax = plt.subplots(figsize=(12, 7))

    ax.set_title("Validation against flood marks", size=14)

    # Plot region
    region.plot(ax=ax, color="grey", linewidth=2, alpha=0.3, label="Region")

    cmap = plt.get_cmap("RdYlGn_r")
    norm = mcolors.BoundaryNorm(bins, cmap.N)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])

    # Bin the 'difference' values and plot
    scores_gdf["binned"] = pd.cut(scores_gdf["difference"], bins=bins, labels=False)

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

    # Add basemap imagery using contextily
    ctx.add_basemap(
        ax,
        crs=scores_gdf.crs.to_string(),
        source=ctx.providers.CartoDB.PositronNoLabels,
    )

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

    fig.savefig(path, dpi=150, bbox_inches="tight")
