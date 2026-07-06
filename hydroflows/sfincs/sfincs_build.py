"""Build a SFINCS model from scratch using hydromt_sfincs."""

import logging
from pathlib import Path
from typing import Optional

from hydromt import log
from hydromt.writers import write_yaml
from hydromt_sfincs import SfincsModel
from workflowpy._typing import FileDirPath, ListOfStr
from workflowpy.method import Method
from workflowpy.parameters import Parameters

from hydroflows.cfg import CFG_DIR, read_recipe
from hydroflows.cfg.utils import find_step_index

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

    catalog_path: Optional[FileDirPath] = None
    """The file path to the data catalog. This is a file in yml format, which should contain the data sources specified in the config file."""


class Output(Parameters):
    """Output parameters for the :py:class:`SfincsBuild` method."""

    sfincs_inp: FileDirPath
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

    model_root: Path
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
    model_root : Path
        The path to the root directory where the SFINCS model will be created, by default "models/sfincs".
    subgrid_output : bool, optional
        Determines whether the sfincs subgrid depth output should exist, by default False.
        In case it is set to True, the setup_subgrid method should be included in the config file.
    src_points_output : bool, optional
        Determines whether the sfincs river source points should exist, by default False.
    **params
        Additional parameters to pass to the SfincsBuild instance.
        See :py:class:`sfincs_build Params <hydroflows.sfincs.sfincs_build.Params>`.

    See Also
    --------
    :py:class:`sfincs_build Input <~hydroflows.sfincs.sfincs_build.Input>`
    :py:class:`sfincs_build Output <~hydroflows.sfincs.sfincs_build.Output>`
    :py:class:`sfincs_build Params <~hydroflows.sfincs.sfincs_build.Params>`
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
        model_root: Path = Path("models/sfincs"),
        subgrid_output: bool = False,
        src_points_output: bool = False,
        **params,
    ) -> None:
        self.params: Params = Params(
            model_root=model_root,
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
                sfincs_subgrid_dep=self.params.model_root
                / "subgrid"
                / "dep_subgrid.tif"
            )

        if self.params.src_points_output:
            optional_outputs.update(
                sfincs_src_points=self.params.model_root / "gis" / "dis.geojson"
            )

        self.output: Output = Output(
            sfincs_inp=self.params.model_root / "sfincs.inp",
            sfincs_region=self.params.model_root / "gis" / "region.geojson",
            **optional_outputs,
        )

    def _run(self):
        """Run the SfincsBuild method."""
        log.initialize_logging(
            file_path=Path(self.params.model_root, "hydromt.log"),
            level=logging.INFO,
        )
        # read the configuration
        _, _, steps = read_recipe(
            self.input.config, settings={"region": self.input.region}
        )

        # throw error if the setup_subgrid is not included in the config but the output is set to True
        if (
            find_step_index(steps, name="subgrid.create") is None
            and self.params.subgrid_output == True
        ):
            raise ValueError(
                "The 'subgrid.create' method must be included in the config file \
in order to set the 'subgrid_output' parameter to True."
            )

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
        )
        # build the model
        sf.build(
            steps=steps,
            write=True,
        )

        # write the opt as yaml
        write_yaml(root / "sfincs_build.yml", {"steps": steps})

        # plot basemap
        if self.params.plot_fig == True:
            sf.plot_basemap(fn_out="basemap.png", plot_region=True, shaded=False)
