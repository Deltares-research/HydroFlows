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
    This file must include a valid coordinate reference system (CRS).
    """

    aoi: Path
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
    """Name of the output file generated for the Sfincs region."""


class SfincsRegion(Method):
    """Rule for deriving a Sfincs region based on the basins draining into an AOI."""

    name: str = "sfincs_region"

    _test_kwargs = {
        "basins": Path("basins.geojson"),
        "aoi": Path("aoi.geojson"),
    }

    def __init__(
        self,
        basins: Path,
        aoi: Path,
        region_root: Path = Path("data/build"),
        **params,
    ) -> None:
        """Create and validate a SfincsRegion instance.

        Parameters
        ----------
        aoi : Path
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

        self.input: Input = Input(basins=basins, aoi=aoi)

        self.output: Output = Output(
            sfincs_region=self.params.region_root / f"{self.params.region_fn}.geojson"
        )

    def run(self):
        """Run the SfincsRegion method."""
        # Read the file with the AOI
        aoi = gpd.read_file(self.input.aoi)

        # Set default CRS if missing
        if aoi.crs is None:
            aoi.set_crs("EPSG:4326", inplace=True)

        # Read the file with the basins/catchments and mask them to the aoi
        aoi_basins = gpd.read_file(
            self.input.basins,
            mask=aoi,
        )

        aoi_basins.to_file(self.output.sfincs_region, driver="GeoJSON")
