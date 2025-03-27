"""Build a FIAT model from scratch using hydromt_fiat."""

from pathlib import Path
from typing import Optional

import geopandas as gpd
import hydromt_fiat
from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_fiat.fiat import FiatModel

from hydroflows._typing import ListOfStr
from hydroflows.cfg import CFG_DIR
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["FIATBuild", "Input", "Output", "Params"]

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

    config: Path = CFG_DIR / "fiat_build.yml"
    """The path to the configuration file (.yml) that defines the settings
    to build a FIAT model. In this file the different model components
    that are required by the :py:class:`hydromt_fiat.fiat.FiatModel` are listed.
    Every component defines the setting for each hydromt_fiat setup methods.
    For more information see hydromt_fiat method
    `documentation <https://deltares.github.io/hydromt_fiat/latest/user_guide/user_guide_overview.html>`_."""

    catalog_path: Optional[Path] = None
    """The file path to the data catalog. This is a file in yml format, which should contain the data sources specified in the config file."""

    ground_elevation: Optional[Path] = None
    """Path to the DEM file with to set ground elevation data."""


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`FIATBuild` method.
    """

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file."""

    spatial_joins_cfg: Path
    """The file path to the FIAT spatial joins configuration (toml) file."""

    ## TODO check if spatial_joins_cfg is created based on config file


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

    predefined_catalogs: Optional[ListOfStr] = None
    """List of predefined data catalogs containing the data sources specified in the config file."""


class FIATBuild(Method):
    """Build a FIAT model from scratch using hydromt_fiat.

    Parameters
    ----------
    region : Path
        The file path to the geometry file that defines the region of interest
        for constructing a FIAT model.
    config : Path
        The path to the configuration file (.yml) that defines the settings
        to build a FIAT model. In this file the different model components
        that are required by the :py:class:`hydromt_fiat.fiat.FiatModel` are listed.
    catalog_path: Optional[Path], optional
        The path to the data catalog file (.yml) that contains the data sources
        specified in the config file. If None (default), a predefined data catalog should be provided.
    predefined_catalogs : Optional[ListOfStr], optional
        A list containing the predefined data catalog names.
    fiat_root : Path
        The path to the root directory where the FIAT model will be created, by default "models/fiat".
    ground_elevation : Optional[Path], optional
        Path to the DEM file with to set ground elevation data, by default None.
    **params
        Additional parameters to pass to the FIATBuild instance.
        See :py:class:`fiat_build Params <hydroflows.methods.fiat.sfincs_build.Params>`.

    See Also
    --------
    :py:class:`fiat_build Input <~hydroflows.methods.fiat.fiat_build.Input>`
    :py:class:`fiat_build Output <~hydroflows.methods.fiat.fiat_build.Output>`
    :py:class:`fiat_build Params <~hydroflows.methods.fiat.fiat_build.Params>`
    :py:class:`hydromt_fiat.fiat.FIATModel`
    """

    name: str = "fiat_build"

    _test_kwargs = {
        "region": Path("region.geojson"),
        "config": Path("hydroflows/cfg/fiat_build.yml"),
        "predefined_catalogs": ["artifact_data"],
    }

    def __init__(
        self,
        region: Path,
        config: Path,
        catalog_path: Optional[Path] = None,
        predefined_catalogs: Optional[ListOfStr] = None,
        fiat_root: Path = "models/fiat",
        ground_elevation: Optional[Path] = None,
        **params,
    ) -> None:
        self.params: Params = Params(
            fiat_root=fiat_root, predefined_catalogs=predefined_catalogs, **params
        )
        self.input: Input = Input(
            region=region,
            config=config,
            ground_elevation=ground_elevation,
            catalog_path=catalog_path,
        )
        if not self.input.catalog_path and not self.params.predefined_catalogs:
            raise ValueError(
                "A data catalog must be specified either via catalog_path or predefined_catalogs."
            )
        self.output: Output = Output(
            fiat_cfg=self.params.fiat_root / "settings.toml",
            spatial_joins_cfg=self.params.fiat_root / "spatial_joins.toml",
        )

    def _run(self):
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
        # Setup the model
        root = self.params.fiat_root
        # Setup logger
        logger = setuplog("fiat_build", log_level="DEBUG")

        data_libs = [FIAT_DATA_PATH]
        if self.params.predefined_catalogs:
            data_libs += self.params.predefined_catalogs
        if self.input.catalog_path:
            data_libs += [self.input.catalog_path]

        model = FiatModel(
            root=root,
            mode="w+",
            data_libs=data_libs,
            logger=logger,
        )

        # Build the model
        model.build(region={"geom": region_gdf}, opt=opt, write=False)

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
