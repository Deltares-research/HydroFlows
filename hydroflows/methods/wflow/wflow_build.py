"""Wflow build method."""

from pathlib import Path
from typing import Optional

from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_wflow import WflowModel
from pydantic import FilePath

from hydroflows._typing import ListOfPath, ListOfStr
from hydroflows.methods.wflow.wflow_utils import plot_basemap
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["WflowBuild"]


class Input(Parameters):
    """Input parameters for the :py:class:`WflowBuild` method."""

    region: Path
    """
    The file path to the geometry file that defines the region of interest
    for constructing a Wflow model for the upstream area draining into
    the specified region. An example of such a file could be the Sfincs region GeoJSON.
    """

    config: FilePath
    """The path to the configuration file (.yml) that defines the settings
    to build a Wflow model. In this file the different model components
    that are required by the :py:class:`hydromt_wflow.WflowModel` are listed.
    Every component defines the setting for each hydromt_wflow setup methods.
    For more information see hydromt_wflow method
    `documentation <https://deltares.github.io/hydromt_wflow/latest/user_guide/wflow_model_setup.html#model-methods>`_
    """

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

    data_libs: ListOfPath | ListOfStr | Path = ["artifact_data"]
    """List of data libraries to be used. This is a predefined data catalog in
    yml format, which should contain the data sources specified in the config file.
    """

    plot_fig: bool = True
    """Determines whether to plot a figure with the
    derived Wflow base maps.
    """


class WflowBuild(Method):
    """Rule for building Wflow model."""

    name: str = "wflow_build"

    _test_kwargs = {
        "region": Path("region.geojson"),
        "config": Path("hydroflows/cfg/wflow_build.yml"),
    }

    def __init__(
        self,
        region: Path,
        config: Path,
        gauges: Path = None,
        wflow_root: Path = "models/wflow",
        **params,
    ) -> None:
        """Create and validate a WflowBuild instance.

        Parameters
        ----------
        region : Path
            The file path to the geometry file that defines the region of interest
            for constructing a wflow model.
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
        self.params: Params = Params(wflow_root=wflow_root, **params)
        self.input: Input = Input(region=region, config=config, gauges=gauges)
        self.output: Output = Output(
            wflow_toml=Path(self.params.wflow_root, "wflow_sbm.toml"),
        )

    def run(self):
        """Run the WflowBuild method."""
        logger = setuplog("build", log_level=20)

        # create the hydromt model
        root = self.output.wflow_toml.parent
        w = WflowModel(
            root=root,
            mode="w+",
            config_fn=self.output.wflow_toml.name,
            data_libs=self.params.data_libs,
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
