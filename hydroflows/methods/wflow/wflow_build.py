"""Wflow build method."""

from pathlib import Path
from typing import List

from hydromt.config import configread
from hydromt.log import setuplog
from hydromt_wflow import WflowModel
from pydantic import BaseModel, FilePath

from hydroflows.methods._validators import ParamsHydromt
from hydroflows.methods.method import HYDROMT_CONFIG_DIR, Method

__all__ = ["WflowBuild"]


class Input(BaseModel):
    """Input parameters."""

    sfincs_region: FilePath


class Output(BaseModel):
    """Output parameters."""

    wflow_toml: Path


class Params(ParamsHydromt):
    """Parameters."""

    # optional parameters
    config: Path = Path(HYDROMT_CONFIG_DIR, "wflow_build.yaml")
    data_libs: List[str] = ["artifact_data"]
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

        # specify region
        region = {
            "subbasin": self.input.sfincs_region,
            "uparea": self.params.upstream_area,
        }

        # read the configuration
        opt = configread(self.params.config)

        # chech whether the sfincs src file was generated
        sfincs_src_points_fn = self.input.sfincs_region.parent / "src.geojson"

        if sfincs_src_points_fn.exists():
            # if so adjust config
            step = dict(
                setup_gauges1=dict(
                    gauges_fn=str(sfincs_src_points_fn),
                    snap_to_river=True,
                    derive_subcatch=False,
                    index_col="index",
                    basename="locs",
                )
            )
            opt.update(step)

        # create the hydromt model
        root = self.output.wflow_toml.parent
        w = WflowModel(
            root=root,
            mode="w+",
            config_fn=self.output.wflow_toml.name,
            data_libs=self.params.data_libs,
            logger=logger,
        )
        # build the model
        w.build(region=region, opt=opt)
