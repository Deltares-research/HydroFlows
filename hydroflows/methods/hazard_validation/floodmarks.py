"""Validate simulated hazard maps using floodmarks method."""

from pathlib import Path
from typing import Literal

import geopandas as gpd
import hydromt
import pandas as pd
import xarray as xr
from shapely.geometry import Point
from sklearn.metrics import mean_squared_error, r2_score

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


class Input(Parameters):
    """Input parameters for the :py:class:`FloodmarksValidation` method."""

    floodmarks_geom: Path
    """
    The file path to a geometry file (shapefile, GeoJSON or GeoPackage) containing the locations of
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
            / f"{self.input.floodmarks_geom.stem}_validation{self.input.floodmarks_geom.suffix}",
            validation_scores_csv=self.params.out_root / self.params.filename,
        )

    def run(self):
        """Run the FloodmarksValidation method."""
        # File extension to driver mapping
        driver_map = {".shp": "ESRI Shapefile", ".geojson": "GeoJSON", ".gpkg": "GPKG"}

        driver = driver_map.get(self.input.floodmarks_geom.suffix, None)
        if driver is None:
            raise ValueError(
                f"Unsupported file extension: {self.input.floodmarks_geom.suffix}"
            )

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

        # Calculate RMSE and R²
        rmse = mean_squared_error(
            gdf_in_region[self.params.waterlevel_col],
            gdf_in_region["modeled_value"],
            squared=False,
        )
        r2 = r2_score(
            gdf_in_region[self.params.waterlevel_col], gdf_in_region["modeled_value"]
        )

        # Create a df with the scores and convert it to a csv
        metrics = {"rmse": [rmse], "r2": [r2]}
        df_metrics = pd.DataFrame(metrics)
        df_metrics.to_csv(self.output.validation_scores_csv, index=False)

        # Export the validated gdf
        gdf_in_region.to_file(self.output.validation_scores_geom, driver=driver)


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
    if geometry.geom_type == "MultiPoint":  # Check if geometry is of type MultiPoint
        points = geometry.geoms  # Access the individual points in the MultiPoint
        if len(points) > 0:  # Check if there are points in the MultiPoint
            # Return the first point (handle 3D if z-coordinate is present)
            return Point(points[0].x, points[0].y, getattr(points[0], "z", 0))
    return geometry  # Return the original geometry if it's not a MultiPoint
