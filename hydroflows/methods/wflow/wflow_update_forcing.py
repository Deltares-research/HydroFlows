from typing import List
from ..method import Method
from pydantic import BaseModel, FilePath
from pathlib import Path

from hydromt_wflow import WflowModel
from hydromt.log import setuplog
import os

__all__ = ["WflowUpdateForcing"]

class Input(BaseModel):
    wflow_toml_default: FilePath

class Output(BaseModel):
    wflow_toml_updated: Path

class Params(BaseModel):
    start_time: str
    end_time: str

    timestep: int = 86400 # in seconds

    data_libs: List[str] = ["artifact_data"]

    precip_src: str = "era5"
    temp_pet_src: str = "era5"
    dem_forcing_src: str = "era5_orography"
    pet_calc_method: str = "debruin"

class WflowUpdateForcing(Method):
    """
    Rule for updating Wflow forcing
    """
    name: str = "wflow_update_forcing"
    params: Params = Params()
    input: Input
    output: Output

    def run(self):
        logger = setuplog("update", log_level=20)

        root = self.input.wflow_toml_default.parent
    
        w = WflowModel(
            root=root,
            mode="r",
            config_fn = self.input.wflow_toml_default,
            data_libs = [
                self.params.data_libs
            ],
            logger=logger,
            )
        
        w.read()

        sims_root = self.output.wflow_toml_updated.parent

        # actually the path doesn't exist, but we create it every time. (ask Dirk)
        w.set_root(
        root=sims_root,
        mode="w+",
        )
    
        w.setup_config(
            **{
            "starttime": self.params.start_time,
            "endtime": self.params.end_time,
            "timestepsecs": self.params.timestep,
            "input.path_forcing": "forcing.nc"
            }
        ) 

        w.setup_precip_forcing(
            precip_fn=self.params.precip_src,
            precip_clim_fn=None,
        )

        w.setup_temp_pet_forcing(
            temp_pet_fn=self.params.temp_pet_src,
            press_correction=True,
            temp_correction=True,
            dem_forcing_fn=self.params.dem_forcing_src,
            pet_method= self.params.pet_calc_method,
            skip_pet=False,
        )
        
        w.set_config("input.path_static", os.path.join(root, "staticmaps.nc"))
        w.write_config(config_name=os.path.basename(self.output.wflow_toml_updated))
        w.write_forcing()