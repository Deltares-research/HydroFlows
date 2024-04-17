"""Wflow build method."""

from pathlib import Path
from typing import Optional

from hydromt.config import configread
from hydromt.log import setuplog
from hydromt_wflow import WflowModel
from pydantic import BaseModel, FilePath

from hydroflows._typing import ListOfStr
from hydroflows.methods.method import HYDROMT_CONFIG_DIR, Method

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
            "subbasin": self.input.region,
            "uparea": self.params.upstream_area,
        }

        # read the configuration
        opt = configread(self.params.config)

        # for reservoirs, lakes and glaciers: check if data is available
        for key in ["reservoirs", "lakes", "glaciers"]:
            if opt[f"setup_{key}"].get(f"{key}_fn") not in w.data_catalog.sources:
                opt.pop(f"setup_{key}")

        # chech whether the sfincs src file was generated
        gauges = self.params.gauges
        if gauges is None or not gauges.is_file():  # remove placeholder
            opt.pop("setup_gauges")
        else:  # replace placeholder with actual file
            step = dict(
                setup_gauges=dict(
                    gauges_fn=str(gauges),
                    snap_to_river=True,
                    derive_subcatch=False,
                    index_col="index",
                    basename="locs",
                )
            )
            opt.update(step)

        # build the model
        w.build(region=region, opt=opt)
