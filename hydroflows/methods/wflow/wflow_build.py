"""Wflow build method."""

from pathlib import Path
from typing import Optional

from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_wflow import WflowModel
from pydantic import BaseModel, FilePath

from hydroflows._typing import ListOfStr
from hydroflows.methods.method import HYDROMT_CONFIG_DIR, Method
from hydroflows.methods.wflow.wflow_utils import plot_basemap

__all__ = ["WflowBuild"]


class Input(BaseModel):
    """Input parameters."""

    region: FilePath


class Output(BaseModel):
    """Output parameters."""

    wflow_toml: Path


class Params(BaseModel):
    """Parameters."""

    # optional parameters
    config: Path = Path(HYDROMT_CONFIG_DIR, "wflow_build.yaml")
    data_libs: ListOfStr = ["artifact_data"]
    gauges: Optional[Path] = None
    upstream_area: int = 30
    plot_fig: bool = True


class WflowBuild(Method):
    """Rule for building Wflow for the upstream area of the Sfincs boundaries."""

    name: str = "wflow_build"
    params: Params = Params()  # optional parameters
    input: Input
    output: Output

    def run(self):
        """Run the Wflow build method."""
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
            "uparea": self.params.upstream_area,
        }

        # read the configuration
        opt = configread(self.params.config)

        # update placeholders in the config
        opt["setup_basemaps"].update(region=region)
        opt["setup_rivers"].update(river_upa=self.params.upstream_area)

        # for reservoirs, lakes and glaciers: check if data is available
        for key in [
            item
            for item in ["reservoirs", "lakes", "glaciers"]
            if f"setup_{item}" in opt
        ]:
            if opt[f"setup_{key}"].get(f"{key}_fn") not in w.data_catalog.sources:
                opt.pop(f"setup_{key}")

        # chech whether the sfincs src file was generated
        gauges = self.params.gauges
        if gauges is None or not gauges.is_file():  # remove placeholder
            opt.pop("setup_gauges")
            opt.pop("setup_config_output_timeseries")
        else:  # replace placeholder with actual file
            opt["setup_gauges"]["gauges_fn"] = str(gauges)

        # build the model
        w.build(opt=opt)

        # write the configuration
        configwrite(root / "wflow_build.yaml", opt)

        # plot basemap
        if self.params.plot_fig:
            _ = plot_basemap(w, fn_out="wflow_basemap.png")
