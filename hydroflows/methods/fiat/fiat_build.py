"""Module/ Rule for building FIAT models."""

from pathlib import Path
from typing import Optional, Union

import geopandas as gpd
import hydromt_fiat
from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_fiat.fiat import FiatModel
from pydantic import FilePath

from hydroflows._typing import DataCatalogPath
from hydroflows.cfg import CFG_DIR
from hydroflows.methods.fiat.fiat_utils import new_column_headers
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["FIATBuild"]

FIAT_DATA_PATH = Path(
    Path(hydromt_fiat.__file__).parent,
    "data",
    "hydromt_fiat_catalog_global.yml",
).as_posix()


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`FIATBuild` method.
    """

    region: Path
    """
    The file path to the geometry file that defines the region of interest
    for constructing a FIAT model.
    """

    config: FilePath = CFG_DIR / "fiat_build.yml"
    """The path to the configuration file (.yml) that defines the settings
    to build a FIAT model. In this file the different model components
    that are required by the :py:class:`hydromt_fiat.fiat.FiatModel` are listed.
    Every component defines the setting for each hydromt_fiat setup methods.
    For more information see hydromt_fiat method
    `documentation <https://deltares.github.io/hydromt_fiat/latest/user_guide/user_guide_overview.html>`_."""

    ground_elevation: Optional[Path] = None
    """Path to the DEM file with to set ground elevation data."""


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`FIATBuild` method.
    """

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file."""


class Params(Parameters):
    """Parameters for the :py:class:`FIATBuild`.

    Instances of this class are used in the :py:class:`FIATBuild`
    method to define the required settings.

    See Also
    --------
    :py:class:`hydromt_fiat.fiat.FiatModel`
        For more details on the FiatModel used in hydromt_fiat.
    """

    fiat_root: Path
    """The path to the root directory where the FIAT model will be created."""

    data_libs: DataCatalogPath = ["artifact_data"]
    """List of data libraries to be used. This is a predefined data catalog in
    yml format, which should contain the data sources specified in the config file."""

    res_x: Union[int, float]
    """The x-resolution to aggregate the model region into a default grid."""

    res_y: Union[int, float]
    """The y-resolution to aggregate the model region into a default grid."""


class FIATBuild(Method):
    """Rule for building FIAT."""

    name: str = "fiat_build"

    _test_kwargs = {
        "region": Path("region.geojson"),
        "config": Path("hydroflows/cfg/fiat_build.yml"),
    }

    def __init__(
        self,
        region: Path,
        config: Path,
        fiat_root: Path = "models/fiat",
        ground_elevation: Optional[Path] = None,
        **params,
    ) -> None:
        """Create and validate a FIATBuild instance.

        Parameters
        ----------
        region : Path
            The file path to the geometry file that defines the region of interest
            for constructing a FIAT model.
        fiat_root : Path
            The path to the root directory where the FIAT model will be created, by default "models/fiat".
        ground_elevation : Optional[Path], optional
            Path to the DEM file with to set ground elevation data, by default None.
        **params
            Additional parameters to pass to the FIATBuild instance.
            See :py:class:`fiat_build Params <hydroflows.methods.fiat.sfincs_build.Params>`.

        See Also
        --------
        :py:class:`fiat_build Input <~hydroflows.methods.fiat.fiat_build.Input>`,
        :py:class:`fiat_build Output <~hydroflows.methods.fiat.fiat_build.Output>`,
        :py:class:`fiat_build Params <~hydroflows.methods.fiat.fiat_build.Params>`,
        :py:class:`hydromt_fiat.fiat.FIATModel`
        """
        self.params: Params = Params(fiat_root=fiat_root, **params)
        self.input: Input = Input(
            region=region, config=config, ground_elevation=ground_elevation
        )
        self.output: Output = Output(fiat_cfg=self.params.fiat_root / "settings.toml")

    def run(self):
        """Run the FIATBuild method."""
        # Read template config
        opt = configread(self.input.config)
        # add optional ground elevation
        if self.input.ground_elevation is not None:
            if "setup_exposure_buildings" not in opt:
                raise ValueError(
                    "The 'setup_exposure_buildings' section is required to set ground elevation."
                )
            opt["setup_exposure_buildings"][
                "ground_elevation"
            ] = self.input.ground_elevation.as_posix()
            opt["setup_exposure_buildings"]["grnd_elev_unit"] = "meters"
        # Add additional information
        region_gdf = gpd.read_file(self.input.region.as_posix())
        region_gdf = region_gdf.dissolve()
        # Select only geometry in case gdf contains more columns
        # Hydromt-fiat selects first column for geometry when fetching OSM
        region_gdf = region_gdf[["geometry"]]
        # If aggregation areas is None, create aggregation vector layer
        if "setup_aggregation_areas" not in opt:
            opt["setup_aggregation_areas"]["aggregation_area_fn"] = "default"
            opt["setup_aggregation_areas"]["res_x"] = self.params.res_x
            opt["setup_aggregation_areas"]["res_y"] = self.params.res_y
        # Setup the model
        root = self.params.fiat_root
        #
        logger = setuplog("fiat_build", log_level="DEBUG")
        model = FiatModel(
            root=root,
            mode="w+",
            data_libs=[FIAT_DATA_PATH] + self.params.data_libs,
            logger=logger,
        )

        # Build the model
        model.build(region={"geom": region_gdf}, opt=opt, write=False)

        # Set the column headers for newer FIAT verions
        # TODO remove once HydroMT-FIAT supports this
        model.exposure.exposure_db.rename(
            new_column_headers(model.exposure.exposure_db.columns),
            axis=1,
            inplace=True,
        )
        for geom in model.exposure.exposure_geoms:
            geom.rename(new_column_headers(geom.columns), axis=1, inplace=True)

        # Write to drive
        model.write()

        # Write opt as yaml
        configwrite(root / "fiat_build.yaml", opt)

        # remove empty directories using pathlib
        for d in root.iterdir():
            if d.is_dir() and not list(d.iterdir()):
                d.rmdir()


if __name__ == "__main__":
    pass
