"""Wflow update forcing method."""
import os
from pathlib import Path
from typing import List

from hydromt.log import setuplog
from hydromt_wflow import WflowModel
from pydantic import BaseModel, FilePath

from ..method import Method

__all__ = ["WflowUpdateForcing"]

class Input(BaseModel):
    """Input parameters."""

    wflow_toml_default: FilePath

class Output(BaseModel):
    """Output parameters."""

    wflow_toml_updated: Path

class Params(BaseModel):
    """Parameters."""

    start_time: str
    end_time: str

    timestep: int = 86400 # in seconds

    data_libs: List[str] = ["artifact_data"]

    precip_src: str = "era5"
    temp_pet_src: str = "era5"
    dem_forcing_src: str = "era5_orography"
    pet_calc_method: str = "debruin"

class WflowUpdateForcing(Method):
    """Rule for updating Wflow forcing."""

    name: str = "wflow_update_forcing"
    params: Params = Params()
    input: Input
    output: Output

    def run(self):
        """Run the WflowUpdateForcing method."""
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

        # add a netcdf output for the discharges
        w.setup_config_output_timeseries(
        mapname="wflow_gauges",
        toml_output="netcdf",
        header=["Q"],
        param = ["lateral.river.q_av"],
        )

        w.set_config("input.path_static", os.path.join(root, "staticmaps.nc"))
        w.write_config(config_name=os.path.basename(self.output.wflow_toml_updated))
        w.write_forcing()
