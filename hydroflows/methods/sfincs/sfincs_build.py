"""SFINCS build methods."""
from pathlib import Path

from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel

from hydroflows._typing import ListOfStr
from hydroflows.config import HYDROMT_CONFIG_DIR
from hydroflows.methods.method import Method

__all__ = ["SfincsBuild"]


class Input(BaseModel):
    """Input parameters for the :py:class:`SfincsBuild` method."""

    region: Path
    """
    The file path to the geometry file that defines the region of interest
    for constructing a SFINCS model.
    """


class Output(BaseModel):
    """Output parameters for the :py:class:`SfincsBuild` method."""

    sfincs_inp: Path
    """The path to the Sfincs configuration (inp) file."""

    sfincs_region: Path
    """The path to the derived Sfincs region GeoJSON file."""


class Params(BaseModel):
    """Parameters for the :py:class:`SfincsBuild`.

    See Also
    --------
    :py:class:`hydromt_sfincs.SfincsModel`
        For more details on the SfincsModel used in hydromt_sfincs.
    """

    # optional parameter
    data_libs: ListOfStr = ["artifact_data"]
    """List of data libraries to be used. This is a predefined data catalog in
    yml format, which should contain the data sources specified in the config file.
    """

    config: Path = Path(HYDROMT_CONFIG_DIR, "sfincs_build.yaml")
    """The path to the configuration file (.yml) that defines the settings
    to build a Sfincs model. In this file the different model components
    that are required by the :py:class:`hydromt_sfincs.SfincsModel` are listed.
    Every component defines the setting for each hydromt_sfincs setup methods.
    For more information see hydromt_sfincs method
    `documentation <https://deltares.github.io/hydromt_sfincs/latest/user_guide/intro.html>`_.
    """

    res: float = 50.0
    """Model resolution [m]."""

    river_upa: float = 30
    """River upstream area threshold [km2]."""

    plot_fig: bool = True
    """Determines whether to plot a figure with the
    derived Sfincs base maps.
    """


class SfincsBuild(Method):
    """Rule for building Sfincs.

    This class utilizes the :py:class:`Params <hydroflows.methods.sfincs.sfincs_build.Params>`,
    :py:class:`Input <hydroflows.methods.sfincs.sfincs_build.Input>`, and
    :py:class:`Output <hydroflows.methods.sfincs.sfincs_build.Output>` classes to build
    a Sfincs model.
    """

    name: str = "sfincs_build"
    params: Params = Params()  # optional parameters
    input: Input
    output: Output

    def run(self):
        """Run the SfincsBuild method."""
        # read the configuration
        opt = configread(self.params.config)
        # update placeholders in the config
        opt["setup_grid_from_region"].update(
            res=self.params.res, region={"geom": str(self.input.region)}
        )
        opt["setup_mask_active"].update(mask=str(self.input.region))
        opt["setup_river_inflow"].update(river_upa=self.params.river_upa)
        # create the hydromt model
        root = self.output.sfincs_inp.parent
        sf = SfincsModel(
            root=root,
            mode="w+",
            data_libs=self.params.data_libs,
            logger=setuplog("sfincs_build", log_level=20),
        )
        # build the model
        sf.build(opt=opt)

        # write the opt as yaml
        configwrite(root / "sfincs_build.yaml", opt)

        # plot basemap
        if self.params.plot_fig == True:
            sf.plot_basemap(fn_out="basemap.png", plot_region=True, shaded=False)
