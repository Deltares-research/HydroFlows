from typing import List
from ..method import Method
from ...templates import TEMPLATE_DIR

from pydantic import BaseModel, FilePath
from pathlib import Path

from hydromt_wflow import WflowModel
from hydromt.config import configread
from hydromt.log import setuplog

import geopandas as gpd

__all__ = ["WflowBuild"]

class Input(BaseModel):
    sfincs_boundaries: FilePath

class Output(BaseModel):
    wflow_inp: Path

class Params(BaseModel):
    # optional parameters 
    config: Path = Path(TEMPLATE_DIR, "wflow_build.yaml")
    data_libs: List[str] = ["artifact_data"]
    strord: int = 4

class WflowBuild(Method):
    """
    Rule for building Wflow for the upstream area of the Sfincs boundaries.
    """
    name: str = "wflow_build"
    params: Params = Params() # optional parameters
    input: Input
    output: Output

    def run(self):
        logger = setuplog("build", log_level=20)
        # read the Sfincs geometry file containing the boundary points required for building the upstream Wflow model
        gdf = gpd.read_file(self.input.sfincs_boundaries)
        # define the target coordinate reference system as EPSG 4326
        tgt_crs = 'EPSG:4326'    
        # reproject the GeoDataFrame to the target CRS
        gdf = gdf.to_crs(tgt_crs)  
        # extract transformed coordinates into lists
        x_coords_list = list(gdf.geometry.x)
        y_coords_list = list(gdf.geometry.y)
        # create the desired list format that will be used as the region argument in the Wflow build
        region_lists = [x_coords_list, y_coords_list]
        # specify region 
        region = {
            "subbasin": region_lists,
            "strord": self.params.strord,
        }
        # read the configuration
        opt = configread(self.params.config)
        # create the hydromt model
        root = self.output.wflow_inp.parent
        w = WflowModel(
            root=root,
            mode="w+",
            config_fn=None,
            data_libs=self.params.data_libs,
            logger=logger
        )
        # build the model
        w.build(region=region, opt=opt)