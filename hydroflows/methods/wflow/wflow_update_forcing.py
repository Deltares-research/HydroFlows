"""Wflow update forcing method."""

import os
from pathlib import Path
from typing import List

from hydromt.log import setuplog
from hydromt_wflow import WflowModel
from pydantic import BaseModel, FilePath

from hydroflows.methods._validators import ParamsHydromt
from hydroflows.methods.method import Method

__all__ = ["WflowUpdateForcing"]


class Input(BaseModel):
    """Input parameters."""

    wflow_toml: FilePath


class Output(BaseModel):
    """Output parameters."""

    wflow_toml: Path


class Params(ParamsHydromt):
    """Parameters."""

    start_time: str = "2010-02-01T00:00:00"
    end_time: str = "2010-02-10T00:00:00"

    timestep: int = 86400  # in seconds

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

        root = self.input.wflow_toml.parent

        w = WflowModel(
            root=root,
            mode="r",
            config_fn=self.input.wflow_toml,
            data_libs=self.params.data_libs,
            logger=logger,
        )


        w.setup_config(
            **{
                "starttime": self.params.start_time,
                "endtime": self.params.end_time,
                "timestepsecs": self.params.timestep,
                "input.path_forcing": "forcing.nc",
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
            pet_method=self.params.pet_calc_method,
            skip_pet=False,
        )


        # add a netcdf output for the discharges
        w.setup_config_output_timeseries(
            mapname="wflow_gauges",
            toml_output="netcdf",
            header=["Q"],
            param=["lateral.river.q_av"],
        )


        if self.output.wflow_toml.is_relative_to(root):
            rel_dir = Path(os.path.relpath(root, self.output.wflow_toml.parent))
        else:
            rel_dir = root
        w.set_config("input.path_static", rel_dir / "staticmaps.nc")

        # write to new root
        sims_root = self.output.wflow_toml.parent

        w.set_root(
            root=sims_root,
            mode="w+",
        )
        w.write_config(config_name=self.output.wflow_toml.name)
        w.write_forcing()
