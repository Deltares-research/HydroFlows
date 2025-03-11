"""Build a SFINCS model from scratch using hydromt_sfincs."""

from pathlib import Path
from typing import Optional

from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_sfincs import SfincsModel

from hydroflows._typing import ListOfStr
from hydroflows.cfg import CFG_DIR
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsBuild", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`SfincsBuild` method."""

    region: Path
    """
    The file path to the geometry file that defines the region of interest
    for constructing a SFINCS model.
    """

    config: Path = CFG_DIR / "sfincs_build.yml"
    """
    The path to the configuration file (.yml) that defines the settings
    to build a SFINCS model. In this file the different model components
    that are required by the :py:class:`hydromt_sfincs.SfincsModel` are listed.
    Every component defines the setting for each hydromt_sfincs setup methods.
    For more information see hydromt_sfincs method
    `documentation <https://deltares.github.io/hydromt_sfincs/latest/user_guide/intro.html>`_.
    """

    catalog_path: Optional[Path] = None
    """The file path to the data catalog. This is a file in yml format, which should contain the data sources specified in the config file."""


class Output(Parameters):
    """Output parameters for the :py:class:`SfincsBuild` method."""

    sfincs_inp: Path
    """The path to the SFINCS configuration (inp) file."""

    sfincs_region: Path
    """The path to the derived SFINCS region GeoJSON file."""

    sfincs_subgrid_dep: Optional[Path] = None
    """The path to the derived SFINCS subgrid depth geotiff file."""

    sfincs_src_points: Optional[Path] = None
    """The path to the derived river source points GeoJSON file."""


class Params(Parameters):
    """Parameters for the :py:class:`SfincsBuild`.

    See Also
    --------
    :py:class:`hydromt_sfincs.SfincsModel`
        For more details on the SfincsModel used in hydromt_sfincs.
    """

    sfincs_root: Path
    """The path to the root directory where the SFINCS model will be created."""

    # optional parameter
    predefined_catalogs: Optional[ListOfStr] = None
    """List of predefined data catalogs containing the data sources specified in the config file."""

    plot_fig: bool = True
    """Determines whether to plot a figure with the
    derived SFINCS base maps.
    """

    subgrid_output: bool = False
    """Determines whether the sfincs subgrid depth output should exist."""

    src_points_output: bool = False
    """Determines whether the sfincs river source points should exist."""


class SfincsBuild(Method):
    """Build a SFINCS model from scratch using hydromt_sfincs.

    Parameters
    ----------
    region : Path
        The file path to the geometry file that defines the region of interest
        for constructing a SFINCS model.
    config : Path
        The path to the configuration file (.yml) that defines the settings
        to build a SFINCS model. In this file the different model components
        that are required by the :py:class:`hydromt_sfincs.sfincs.SfincsModel` are listed.
    catalog_path: Optional[Path], optional
        The path to the data catalog file (.yml) that contains the data sources
        specified in the config file. If None (default), a predefined data catalog should be provided.
    predefined_catalogs : Optional[ListOfStr], optional
        A list containing the predefined data catalog names.
    sfincs_root : Path
        The path to the root directory where the SFINCS model will be created, by default "models/sfincs".
    subgrid_output : bool, optional
        Determines whether the sfincs subgrid depth output should exist, by default False.
        In case it is set to True, the setup_subgrid method should be included in the config file.
    src_points_output : bool, optional
        Determines whether the sfincs river source points should exist, by default False.
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

    name: str = "sfincs_build"

    _test_kwargs = {
        "region": Path("region.geojson"),
        "config": CFG_DIR / "sfincs_build.yml",
        "catalog_path": Path("data_catalog.yml"),
    }

    def __init__(
        self,
        region: Path,
        config: Path = CFG_DIR / "sfincs_build.yml",
        catalog_path: Optional[Path] = None,
        predefined_catalogs: Optional[ListOfStr] = None,
        sfincs_root: Path = Path("models/sfincs"),
        subgrid_output: bool = False,
        src_points_output: bool = False,
        **params,
    ) -> None:
        self.params: Params = Params(
            sfincs_root=sfincs_root,
            predefined_catalogs=predefined_catalogs,
            subgrid_output=subgrid_output,
            src_points_output=src_points_output,
            **params,
        )
        self.input: Input = Input(
            region=region,
            config=config,
            catalog_path=catalog_path,
        )
        if not self.input.catalog_path and not self.params.predefined_catalogs:
            raise ValueError(
                "A data catalog must be specified either via catalog_path or predefined_catalogs."
            )

        optional_outputs = {}
        if self.params.subgrid_output:
            optional_outputs.update(
                sfincs_subgrid_dep=self.params.sfincs_root
                / "subgrid"
                / "dep_subgrid.tif"
            )

        if self.params.src_points_output:
            optional_outputs.update(
                sfincs_src_points=self.params.sfincs_root / "gis" / "src.geojson"
            )

        self.output: Output = Output(
            sfincs_inp=self.params.sfincs_root / "sfincs.inp",
            sfincs_region=self.params.sfincs_root / "gis" / "region.geojson",
            **optional_outputs,
        )

    def _run(self):
        """Run the SfincsBuild method."""
        # read the configuration
        opt = configread(self.input.config)

        # throw error if the setup_subgrid is not included in the config but the output is set to True
        if "setup_subgrid" not in opt and self.params.subgrid_output == True:
            raise ValueError(
                "The 'setup_subgrid' method must be included in the config file in order to set the 'subgrid_output' parameter to True."
            )

        # update placeholders in the config
        opt["setup_grid_from_region"].update(region={"geom": str(self.input.region)})
        opt["setup_mask_active"].update(mask=str(self.input.region))

        data_libs = []
        if self.params.predefined_catalogs:
            data_libs += self.params.predefined_catalogs
        if self.input.catalog_path:
            data_libs += [self.input.catalog_path]

        # create the hydromt model
        root = self.output.sfincs_inp.parent
        sf = SfincsModel(
            root=root,
            mode="w+",
            data_libs=data_libs,
            logger=setuplog("sfincs_build", log_level=20),
        )
        # build the model
        sf.build(opt=opt)

        # write the opt as yaml
        configwrite(root / "sfincs_build.yaml", opt)

        # plot basemap
        if self.params.plot_fig == True:
            sf.plot_basemap(fn_out="basemap.png", plot_region=True, shaded=False)
