"""SFINCS region methods."""

from pathlib import Path

import geopandas as gpd

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsRegion"]


class Input(Parameters):
    """Input parameters for the :py:class:`SfincsRegion` method."""

    subbasins: Path
    """
    The file path to the geometry file containing hydrological (sub)basins/catchments.
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


class SfincsRegion(Method):
    """Rule for deriving a Sfincs region based on the basins draining into an AOI."""

    name: str = "sfincs_region"

    _test_kwargs = {
        "subbasins": Path("subbasins.geojson"),
        "aoi": Path("aoi.geojson"),
    }

    def __init__(
        self,
        subbasins: Path,
        aoi: Path,
        sfincs_region: Path = Path("sfincs_region.geojson"),
    ) -> None:
        """Create and validate a SfincsRegion instance.

        Parameters
        ----------
        aoi : Path
            The file path the geometry file defining the Area of Interest (AOI).
        subbasins : Path
            The file path to the geometry file containing hydrological (sub)basins/catchments.
            Basins intersecting with the Area of Interest (AOI) will be retained.
        region : Path, optional
            The file path to the derived sfincs region, by default "sfincs_region.geojson".

        See Also
        --------
        :py:class:`SfincsRegion Input <hydroflows.methods.sfincs.sfincs_region.Input>`
        :py:class:`SfincsRegion Output <hydroflows.methods.sfincs.sfincs_region.Output>`
        """
        self.input: Input = Input(subbasins=subbasins, aoi=aoi)

        self.output: Output = Output(sfincs_region=sfincs_region)

    def run(self):
        """Run the SfincsRegion method."""
        # Read the file with the AOI
        aoi = gpd.read_file(self.input.aoi)

        # Raise an error if CRS is missing
        if aoi.crs is None:
            raise ValueError(
                "The Coordinate Reference System (CRS) is missing from the AOI input file. "
                "Please define a CRS."
            )

        # Read the file with the basins/catchments and mask them to the aoi
        aoi_subbasins = gpd.read_file(
            self.input.subbasins,
            mask=aoi,
        )

        aoi_subbasins.to_file(self.output.sfincs_region, driver="GeoJSON")
