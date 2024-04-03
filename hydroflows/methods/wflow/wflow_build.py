"""Wflow build method."""
from pathlib import Path
from typing import List

import geopandas as gpd
from hydromt.config import configread
from hydromt.log import setuplog
from hydromt_wflow import WflowModel
from pydantic import BaseModel, FilePath

from hydroflows.methods.method import HYDROMT_CONFIG_DIR, Method, ParamsHydromt

__all__ = ["WflowBuild"]

class Input(BaseModel):
    """Input parameters."""

    sfincs_src_points: FilePath

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
    params: Params = Params() # optional parameters
    input: Input
    output: Output

    def run(self):
        """Run the Wflow build method."""
        logger = setuplog("build", log_level=20)
        # read the Sfincs geometry file containing the boundary points
        # required for building the upstream Wflow model
        gdf = gpd.read_file(self.input.sfincs_src_points)
        # define the target coordinate reference system as EPSG 4326
        tgt_crs = 'EPSG:4326'
        # reproject the GeoDataFrame to the target CRS
        gdf = gdf.to_crs(tgt_crs)
        # extract transformed coordinates into lists
        x_coords_list = list(gdf.geometry.x)
        y_coords_list = list(gdf.geometry.y)
        # create the desired list format that will be used as
        # the region argument in the Wflow build
        region_lists = [x_coords_list, y_coords_list]
        # specify region
        region = {
            "subbasin": region_lists,
            "uparea": self.params.upstream_area,
        }
        # read the configuration
        opt = configread(self.params.config)
        # create the hydromt model
        root = self.output.wflow_toml.parent
        w = WflowModel(
            root=root,
            mode="w+",
            config_fn=self.output.wflow_toml.name,
            data_libs=self.params.data_libs,
            logger=logger
        )
        # build the model
        w.build(region=region, opt=opt)
