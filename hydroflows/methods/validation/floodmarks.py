"""Validate simulated hazard maps using floodmarks method."""

from pathlib import Path

import geopandas as gpd
import hydromt

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


class Input(Parameters):
    """Input parameters for the :py:class:`FloodmarksValidation` method."""

    floodmarks_geom = Path
    """
    The file path to the geometry file (shapefile or geojson) including the location of the
    floodmarks as points, as well as an attribute/property with cooresponding water
    levels at these locations.
    """

    flood_hazard_map = Path
    """
    The file path to the generated flood hazard map for validation, in TIFF format.
    """

    region: Path
    """
    The file path to the geometry file including the area used for simulating the hazards.
    An example of such a file could be the SFINCS region GeoJSON.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`FloodmarksValidation` method."""

    validation_scores_csv: Path
    """The path to the CSV file with the derived validation scores."""


class Params(Parameters):
    """Parameters for :py:class:`PluvialDesignEvents` method."""

    scores_root: Path
    """Root folder to save the derived validation scores."""

    waterlevel_prop: str
    """Observed water level property of the input floodmarks geometry file provided in :py:class:`Input` class."""

    filename: str = "validation_scores_floodmarks.csv"
    """The filename for the produced validation scores csv file."""


class FloodmarksValidation(Method):
    """Rule for validating the derived flood hazard maps against floodmarks."""

    name: str = "floodmarks_validation"

    _test_kwargs = {
        "floodmarks_geom": Path("region.geojson"),
        "region": Path("region.geojson"),
    }

    def __init__(
        self,
        floodmarks_geom: Path,
        region: Path,
        flood_hazard_map: Path,
        scores_root: Path = "data/validation",
        waterlevel_prop: str = "water_level_obs",
        **params,
    ):
        """Create and validate a FloodmarksValidation instance.

        Parameters
        ----------
        floodmarks_geom : Path
            The file path to the geometry file including floodmarks.
        region : Path
            text.
        flood_hazard_map : Path
            The file path to the generated flood hazard map for validation.
        scores_root : Path, optional
            The root folder to save the derived validation scores, by default "data/validation".
        waterlevel_prop : Str
            text
        **params
            Additional parameters to pass to the FloodmarksValidation instance.

        See Also
        --------
        :py:class:`FloodmarksValidation Input <hydroflows.methods.validation.floodmarks_validation.Input>`
        :py:class:`FloodmarksValidation Output <hydroflows.methods.validation.floodmarks_validation.Output>`
        :py:class:`FloodmarksValidation Params <hydroflows.methods.validation.floodmarks_validation.Params>`
        """
        self.params: Params = Params(
            scores_root=scores_root, waterlevel_prop=waterlevel_prop, **params
        )
        self.input: Input = Input(
            floodmarks_geom=floodmarks_geom,
            flood_hazard_map=flood_hazard_map,
            region=region,
        )
        self.output: Output = Output(
            validation_scores_csv=self.params.scores_root / self.params.filename
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
        print(
            f"Floodmarks inside the simulated region: {num_floodmarks_inside}, Floodmarks outside: {num_floodmarks_outside}"
        )

        # Read the floodmap
        floodmap = hydromt.io.open_raster(self.input.flood_hazard_map)

        # Sample the floodmap at the floodmark locs
        samples = floodmap.raster.sample(gdf_in_region)

        # Extract modeled values for each point, handling NaN as non-flooded areas
        modeled_values = []
        for idx in samples.index:
            x_coord = samples["x"].sel(index=idx).values
            y_coord = samples["y"].sel(index=idx).values
            # Extract scalar value from the array
            modeled_value = floodmap.sel(x=x_coord, y=y_coord).values.item()
            modeled_values.append(modeled_value)

        # Assign the modeled values to the gdf
        gdf_in_region.loc[:, "modeled_value"] = modeled_values

        # Handle NaN values in 'is_flooded'
        gdf_in_region.loc[:, "is_flooded"] = ~gdf_in_region["modeled_value"].isna()

        # Calculate the difference between observed and modeled values
        gdf_in_region.loc[:, "difference"] = (
            gdf_in_region[self.params.waterlevel_prop] - gdf_in_region["modeled_value"]
        )

        # Filter out non-flooded areas
        # valid_data = gdf_in_region.dropna(subset=['modeled_value', self.params.waterlevel_prop])

        # Calculate RMSE and R² only for the flooded areas
        # rmse = np.sqrt(mean_squared_error(valid_data[self.params.waterlevel_prop], valid_data['modeled_value']))
        # r2 = r2_score(valid_data[self.params.waterlevel_prop], valid_data['modeled_value'])

        # Export gdf as a csv
        gdf_in_region.to_csv(self.output.validation_scores_csv)
