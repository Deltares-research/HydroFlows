"""SFINCS build methods."""

from pathlib import Path
from typing import Optional

from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_sfincs import SfincsModel

from hydroflows._typing import DataCatalogPath
from hydroflows.config import HYDROMT_CONFIG_DIR
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsBuild"]


class Input(Parameters):
    """Input parameters for the :py:class:`SfincsBuild` method."""

    region: Path
    """
    The file path to the geometry file that defines the region of interest
    for constructing a SFINCS model.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`SfincsBuild` method."""

    sfincs_inp: Path
    """The path to the SFINCS configuration (inp) file."""

    sfincs_region: Path
    """The path to the derived SFINCS region GeoJSON file."""

    sfincs_subgrid_dep: Path
    """The path to the derived SFINCS subgrid depth geotiff file."""


class Params(Parameters):
    """Parameters for the :py:class:`SfincsBuild`.

    See Also
    --------
    :py:class:`hydromt_sfincs.SfincsModel`
        For more details on the SfincsModel used in hydromt_sfincs.
    """

    sfincs_root: Path
    """The path to the root directory where the SFINCS model will be created."""

    res: float
    """Model resolution [m]."""

    # optional parameter
    data_libs: DataCatalogPath = ["artifact_data"]
    """List of data libraries to be used. This is a predefined data catalog in
    yml format, which should contain the data sources specified in the config file.
    """

    default_config: Path = Path(HYDROMT_CONFIG_DIR, "sfincs_build.yml")
    """The path to the configuration file (.yml) that defines the settings
    to build a SFINCS model. In this file the different model components
    that are required by the :py:class:`hydromt_sfincs.SfincsModel` are listed.
    Every component defines the setting for each hydromt_sfincs setup methods.
    For more information see hydromt_sfincs method
    `documentation <https://deltares.github.io/hydromt_sfincs/latest/user_guide/intro.html>`_.
    """

    merge_config: Optional[Path] = None
    """The path to a configuration file (.yml) to be merged with the default config."""

    merge_kwargs: Optional[dict] = None
    """Additional keyword arguments to pass to the merge method."""

    river_upa: float = 30
    """River upstream area threshold [km2]."""

    plot_fig: bool = True
    """Determines whether to plot a figure with the
    derived SFINCS base maps.
    """


class SfincsBuild(Method):
    """Rule for building SFINCS model."""

    name: str = "sfincs_build"

    _test_kwargs = {
        "region": Path("region.geojson"),
    }

    def __init__(
        self,
        region: Path,
        sfincs_root: Path = Path("models/sfincs"),
        res: float = 100,
        **params,
    ) -> None:
        """Create and validate a SfincsBuild instance.

        Parameters
        ----------
        region : Path
            The file path to the geometry file that defines the region of interest
            for constructing a SFINCS model.
        sfincs_root : Path
            The path to the root directory where the SFINCS model will be created, by default "models/sfincs".
        res : float, optional
            Model resolution [m], by default 100.
        **params
            Additional parameters to pass to the SfincsBuild instance.
            See :py:class:`sfincs_build Params <hydroflows.methods.sfincs.sfincs_build.Params>`.

        See Also
        --------
        :py:class:`sfincs_build Input <~hydroflows.methods.sfincs.sfincs_build.Input>`
        :py:class:`sfincs_build Output <~hydroflows.methods.sfincs.sfincs_build.Output>`
        :py:class:`sfincs_build Params <~hydroflows.methods.sfincs.sfincs_build.Params>`
        :py:class:`hydromt_sfincs.SfincsModel`
        """
        self.params: Params = Params(sfincs_root=sfincs_root, res=res, **params)
        self.input: Input = Input(region=region)
        self.output: Output = Output(
            sfincs_inp=self.params.sfincs_root / "sfincs.inp",
            sfincs_region=self.params.sfincs_root / "gis" / "region.geojson",
            sfincs_subgrid_dep=self.params.sfincs_root / "subgrid" / "dep_subgrid.tif",
        )

    def run(self):
        """Run the SfincsBuild method."""
        # read the configuration
        opt = configread(self.params.default_config)
        # TODO merge config
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
