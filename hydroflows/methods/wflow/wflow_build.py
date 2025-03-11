"""Build a Wflow model from scratch using hydromt_wflow."""

from pathlib import Path
from typing import Optional

from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_wflow import WflowModel

from hydroflows._typing import ListOfStr
from hydroflows.cfg import CFG_DIR
from hydroflows.methods.wflow.wflow_utils import plot_basemap
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["WflowBuild", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`WflowBuild` method."""

    region: Path
    """
    The file path to the geometry file that defines the region of interest
    for constructing a Wflow model for the upstream area draining into
    the specified region. An example of such a file could be the Sfincs region GeoJSON.
    """

    config: Path = CFG_DIR / "wflow_build.yml"
    """The path to the configuration file (.yml) that defines the settings
    to build a Wflow model. In this file the different model components
    that are required by the :py:class:`hydromt_wflow.WflowModel` are listed.
    Every component defines the setting for each hydromt_wflow setup methods.
    For more information see hydromt_wflow method
    `documentation <https://deltares.github.io/hydromt_wflow/latest/user_guide/wflow_model_setup.html#model-methods>`_
    """

    catalog_path: Optional[Path] = None
    """The file path to the data catalog. This is a file in yml format, which should contain the data sources specified in the config file."""

    gauges: Optional[Path] = None
    """Gauges vector file including the locations of interest to get Wflow simulation outputs.
    The vector file must include a column named 'index' that contains the gauge numbers.
    An example of this vector file is the Sfincs source points GeoJSON, which is necessary
    for coupling Wflow with Sfincs to run, for example, a fluvial flood risk assessment workflow.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`WflowBuild` method."""

    wflow_toml: Path
    """
    The file path to the Wflow (toml) configuration file.
    """


class Params(Parameters):
    """Parameters for the :py:class:`WflowBuild` method.

    See Also
    --------
    :py:class:`hydromt_wflow.WflowModel`
        For more details on the WflowModel used in hydromt_wflow.
    """

    wflow_root: Path
    """The path to the root directory where the wflow model will be created."""

    predefined_catalogs: Optional[ListOfStr] = None
    """List of predefined data catalogs containing the data sources specified in the config file."""

    plot_fig: bool = True
    """Determines whether to plot a figure with the
    derived Wflow base maps.
    """


class WflowBuild(Method):
    """Build a Wflow model from scratch using hydromt_wflow.

    Parameters
    ----------
    region : Path
        The file path to the geometry file that defines the region of interest
        for constructing a wflow model.
    config : Path
        The path to the configuration file (.yml) that defines the settings
        to build a Wflow model. In this file the different model components
        that are required by the :py:class:`hydromt_wflow.wflow.WflowModel` are listed.
    catalog_path: Optional[Path], optional
        The path to the data catalog file (.yml) that contains the data sources
        specified in the config file. If None (default), a predefined data catalog should be provided.
    predefined_catalogs : Optional[ListOfStr], optional
        A list containing the predefined data catalog names.
    wflow_root : Path
        The path to the root directory where the  wflow model will be created, by default "models/wflow".
    **params
        Additional parameters to pass to the WflowBuild instance.
        See :py:class:`wflow_build Params <hydroflows.methods.wflow.wflow_build.Params>`.

    See Also
    --------
    :py:class:`wflow_build Input <hydroflows.methods.wflow.wflow_build.Input>`
    :py:class:`wflow_build Output <hydroflows.methods.wflow.wflow_build.Output>`
    :py:class:`wflow_build Params <hydroflows.methods.wflow.wflow_build.Params>`
    :py:class:`hydromt_wflow.WflowModel`
    """

    name: str = "wflow_build"

    _test_kwargs = {
        "region": Path("region.geojson"),
        "config": CFG_DIR / "wflow_build.yml",
        "catalog_path": Path("data_catalog.yml"),
    }

    def __init__(
        self,
        region: Path,
        config: Path,
        catalog_path: Optional[Path] = None,
        predefined_catalogs: Optional[ListOfStr] = None,
        gauges: Path = None,
        wflow_root: Path = "models/wflow",
        **params,
    ) -> None:
        self.params: Params = Params(
            wflow_root=wflow_root, predefined_catalogs=predefined_catalogs, **params
        )
        self.input: Input = Input(
            region=region, config=config, catalog_path=catalog_path, gauges=gauges
        )
        if not self.input.catalog_path and not self.params.predefined_catalogs:
            raise ValueError(
                "A data catalog must be specified either via catalog_path or predefined_catalogs."
            )
        self.output: Output = Output(
            wflow_toml=Path(self.params.wflow_root, "wflow_sbm.toml"),
        )

    def _run(self):
        """Run the WflowBuild method."""
        logger = setuplog("build", log_level=20)

        data_libs = []
        if self.params.predefined_catalogs:
            data_libs += self.params.predefined_catalogs
        if self.input.catalog_path:
            data_libs += [self.input.catalog_path]

        # create the hydromt model
        root = self.output.wflow_toml.parent
        w = WflowModel(
            root=root,
            mode="w+",
            config_fn=self.output.wflow_toml.name,
            data_libs=data_libs,
            logger=logger,
        )

        # specify region
        region = {
            "subbasin": str(self.input.region),
        }

        # read the configuration
        opt = configread(self.input.config)

        # update placeholders in the config
        opt["setup_basemaps"].update(region=region)

        # for reservoirs, lakes and glaciers: check if data is available
        for key in [
            item
            for item in ["reservoirs", "lakes", "glaciers"]
            if f"setup_{item}" in opt
        ]:
            if opt[f"setup_{key}"].get(f"{key}_fn") not in w.data_catalog.sources:
                opt.pop(f"setup_{key}")

        # check whether the sfincs src file was generated
        gauges = self.input.gauges
        if gauges is None or not gauges.is_file():  # remove placeholder
            for item in ["setup_gauges", "setup_config_output_timeseries"]:
                opt.pop(item, None)
        else:  # replace placeholder with actual file
            opt["setup_gauges"]["gauges_fn"] = str(gauges)

        # build the model
        w.build(opt=opt)

        # write the configuration
        configwrite(root / "wflow_build.yaml", opt)

        # plot basemap
        if self.params.plot_fig:
            _ = plot_basemap(w, fn_out="wflow_basemap.png")
