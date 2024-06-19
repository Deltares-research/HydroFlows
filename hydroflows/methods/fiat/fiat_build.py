"""Module/ Rule for building FIAT models."""
import os
from pathlib import Path

import geopandas as gpd
import hydromt_fiat
from hydromt.config import configread
from hydromt_fiat.fiat import FiatModel
from pydantic import BaseModel, FilePath

from hydroflows._typing import ListOfStr
from hydroflows.methods.method import HYDROMT_CONFIG_DIR, Method

__all__ = ["FIATBuild"]

FIAT_DATA_PATH = Path(
    os.path.dirname(hydromt_fiat.__file__),
    "data",
    "hydromt_fiat_catalog_global.yml",
).as_posix()


class Input(BaseModel):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`FIATBuild` method.
    """

    region: FilePath
    """
    The file path to the geometry file that defines the region of interest
    for constructing a FIAT model.
    """


class Output(BaseModel):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`FIATBuild` method.
    """

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file."""


class Params(BaseModel):
    """Parameters.

    Instances of this class are used in the :py:class:`FIATBuild`
    method to define the required settings.

    See Also
    --------
    :py:class:`hydromt_fiat.fiat.FiatModel`
        For more details on the FiatModel used in hydromt_fiat.
    """

    data_libs: ListOfStr = ["artifact_data"]
    """List of data libraries to be used. This is a predefined data catalog in
    yml format, which should contain the data sources specified in the config file."""

    config: Path = Path(HYDROMT_CONFIG_DIR, "fiat_build.yaml")
    """The path to the configuration file (.yml) that defines the settings
    to build a FIAT model. In this file the different model components
    that are required by the :py:class:`hydromt_fiat.fiat.FiatModel` are listed.
    Every component defines the setting for each hydromt_fiat setup methods.
    For more information see hydromt_fiat method
    `documentation <https://deltares.github.io/hydromt_fiat/latest/user_guide/user_guide_overview.html>`_."""

    continent: str = "South America"
    """Continent of the region of interest."""


class FIATBuild(Method):
    """Rule for building FIAT.

    This class utilizes the :py:class:`Params <hydroflows.methods.fiat.fiat_build.Params>`,
    :py:class:`Input <hydroflows.methods.fiat.fiat_build.Input>`, and
    :py:class:`Output <hydroflows.methods.fiat.fiat_build.Output>` classes to build
    a FIAT model.
    """

    name: str = "fiat_build"
    params: Params = Params()
    input: Input
    output: Output

    def run(self):
        """Run the FIATBuild method."""
        # Read template config
        opt = configread(self.params.config)
        # Add additional information
        region_gdf = gpd.read_file(self.input.region.as_posix()).to_crs(4326)
        region_gdf = region_gdf.dissolve()
        # Select only geometry in case gdf contains more columns
        # Hydromt-fiat selects first column for geometry when fetching OSM
        region_gdf = region_gdf[["geometry"]]
        opt.update({"setup_region": {"region": {"geom": region_gdf}}})
        # Setup the model
        root = self.output.fiat_cfg.parent
        model = FiatModel(
            root=root,
            mode="w+",
            data_libs=[FIAT_DATA_PATH] + self.params.data_libs,
        )
        # Build the model
        model.build(opt=opt)


if __name__ == "__main__":
    pass
