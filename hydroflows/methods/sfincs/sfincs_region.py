"""SFINCS region methods."""

from pathlib import Path

import geopandas as gpd

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsRegion"]


class Input(Parameters):
    """Input parameters for the :py:class:`SfincsRegion` method."""

    basins: Path
    """
    The file path to the geometry file containing hydrological basins/catchments.
    """

    AOI: Path
    """
    The file path the geometry file defining the Area of Interest (AOI).
    This represents the geographic region for which a flood risk assessment will be conducted.
    The AOI file can include boundaries such as a city's administrative limits or any
    other spatial boundary of interest.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`SfincsRegion` method."""

    sfincs_region: Path
    """
    The file path to the geometry file that defines the region of interest
    for constructing a SFINCS model.
    """


class Params(Parameters):
    """Parameters for :py:class:`SfincsRegion` method."""

    region_root: Path
    """Root folder to save the Sfincs region."""

    region_fn: str = "sfincs_region"


class SfincsRegion(Method):
    """Rule for deriving a Sfincs region based on the basins draining into an AOI."""

    name: str = "sfincs_region"

    _test_kwargs = {
        "basins": Path("basins.geojson"),
        "AOI": Path("AOI.geojson"),
    }

    def __init__(
        self,
        basins: Path,
        AOI: Path,
        region_root: Path = Path("data/build"),
        **params,
    ) -> None:
        """Create and validate a SfincsRegion instance.

        Parameters
        ----------
        AOI : Path
            The file path the geometry file defining the Area of Interest (AOI).
        basins : Path
            The file path to the geometry file containing hydrological basins/catchments.
            Basins intersecting with the Area of Interest (AOI) will be retained.
        region_root : Path, optional
            The root folder to save the derived sfincs region, by default "data/build".
        **params
            Additional parameters to pass to the SfincsRegion Params instance.

        See Also
        --------
        :py:class:`SfincsRegion Input <hydroflows.methods.sfincs.sfincs_region.Input>`
        :py:class:`SfincsRegion Output <hydroflows.methods.sfincs.sfincs_region.Output>`
        :py:class:`SfincsRegion Params <hydroflows.methods.sfincs.sfincs_region.Params>`
        """
        self.params: Params = Params(region_root=region_root, **params)

        self.input: Input = Input(basins=basins, AOI=AOI)

        self.output: Output = Output(
            sfincs_region=self.params.region_root / f"{self.params.region_fn}.geojson"
        )

    def run(self):
        """Run the SfincsRegion method."""
        # Read the file with the basins/cathments
        basins = gpd.read_file(self.input.basins)
        # Read the file with the AOI
        aoi = gpd.read_file(self.input.AOI)

        # Set default CRS if missing
        default_crs = "EPSG:4326"
        if aoi.crs is None:
            # TODO change it to logging
            print(
                f"The AOI file provided ({self.input.AOI}) is not georeferenced. Assigning CRS: {default_crs}."
            )
            aoi.set_crs(default_crs, inplace=True)
        if basins.crs is None:
            basins.set_crs(default_crs, inplace=True)

        # Ensure both GDFs use the same CRS
        if aoi.crs != basins.crs:
            basins = basins.to_crs(aoi.crs)

        # Perform the intersection filtering
        filtered_basins = basins[basins.intersects(aoi.unary_union)]

        filtered_basins.to_file(self.output.sfincs_region, driver="GeoJSON")
