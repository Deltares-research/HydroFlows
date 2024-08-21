"""Wflow update forcing method."""

import os
from datetime import datetime
from pathlib import Path

from hydromt.log import setuplog
from hydromt_wflow import WflowModel

from hydroflows._typing import ListOfStr
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["WflowUpdateForcing"]


class Input(Parameters):
    """Input parameters for the :py:class:`WflowUpdateForcing` method."""

    wflow_toml: Path
    """The file path to the Wflow (toml) configuration file from the initial
    Wflow model to be updated."""


class Output(Parameters):
    """Output parameters for the :py:class:`WflowUpdateForcing` method."""

    wflow_out_toml: Path
    """The path to the updated (forcing) Wflow (toml) configuration file."""


class Params(Parameters):
    """Parameters for the :py:class:`WflowUpdateForcing` method.

    See Also
    --------
    :py:class:`hydromt_wflow.WflowModel`
        For more details on the WflowModel used in hydromt_wflow.
    """

    start_time: datetime
    """The start time of the period for which we want to generate forcing."""

    end_time: datetime
    """The end time of the period for which we want to generate forcing."""

    sim_name: str
    """"The name of the subdirectory of the basemodel in which the
    forcing along with the updated config will be saved."""

    timestep: int = 86400  # in seconds
    """The timestep for generated forcing in seconds."""

    data_libs: ListOfStr = ["artifact_data"]
    """List of data libraries to be used. This is a predefined data catalog in
    yml format, which should contain the data sources for precipitation,
    temperature, elevation grid of the climate data (optionally) and
    potential evaporation (PET) estimation."""

    precip_src: str = "era5_daily_zarr"
    """The source for precipitation data."""

    temp_pet_src: str = "era5_daily_zarr"
    """The source for temperature and potential evaporation estimation
    data. Depending on PET estimation method the temp_pet_src
    should contain temperature 'temp' [°C], pressure 'press_msl' [hPa],
    incoming shortwave radiation 'kin' [W/m2], outgoing shortwave
    radiation 'kout' [W/m2], wind speed 'wind' [m/s], relative humidity
    'rh' [%], dew point temperature 'temp_dew' [°C], wind speed either total 'wind'
    or the U- 'wind10_u' [m/s] and V- 'wind10_v' components [m/s]. Required variables
    for De Bruin reference evapotranspiration: 'temp' [°C], 'press_msl' [hPa],
    'kin' [W/m2], 'kout' [W/m2]."""

    dem_forcing_src: str = "era5_orography"
    """The source for the elevation grid of the climate data.
    The temperature will be reprojected and then
    downscaled to model resolution using the elevation lapse rate. If not present,
    the upscaled elevation grid of the wflow model is used ('wflow_dem')."""

    pet_calc_method: str = "debruin"
    """The method used for potential evaporation calculation."""


class WflowUpdateForcing(Method):
    """Rule for updating Wflow forcing."""

    name: str = "wflow_update_forcing"

    def __init__(
        self,
        wflow_toml: Path,
        start_time: datetime,
        end_time: datetime,
        sim_name: str = "default",
        **params,
    ):
        """Create and validate a WflowUpdateForcing instance.

        Wflow updated toml along with the forcing are stored in a simulations
        subdirectory of the basemodel.

        Parameters
        ----------
        wflow_toml : Path
            The file path to the Wflow basemodel configuration file (toml).
        start_time : datetime
            The start time of the period for which we want to generate forcing.
        end_time:datetime
            The end time of the period for which we want to generate forcing
        sim_name : str, optional
           The name of the subdirectory of the basemodel in which the
           forcing along with the updated config will be saved, by default "default".
        **params
            Additional parameters to pass to the WflowUpdateForcing instance.
            See :py:class:`wflow_update_forcing Params <hydroflows.methods.wflow.wflow_update_forcing.Params>`.

        See Also
        --------
        :py:class:`wflow_update_forcing Input <hydroflows.methods.wflow.wflow_update_forcing.Input>`
        :py:class:`wflow_update_forcing Output <hydroflows.methods.wflow.wflow_update_forcing.Output>`
        :py:class:`wflow_update_forcing Params <hydroflows.methods.wflow.wflow_update_forcing.Params>`
        :py:class:`hydromt_wflow.WflowModel`
            For more details on the WflowModel used in hydromt_wflow.
        """
        self.params: Params = Params(
            start_time=start_time, end_time=end_time, sim_name=sim_name, **params
        )
        self.input: Input = Input(wflow_toml=wflow_toml)
        wflow_out_toml = (
            self.input.wflow_toml.parent / "simulations" / sim_name / "wflow_sbm.toml"
        )
        self.output: Output = Output(wflow_out_toml=wflow_out_toml)

    def run(self):
        """Run the WflowUpdateForcing method."""
        logger = setuplog("update", log_level=20)

        root = self.input.wflow_toml.parent

        w = WflowModel(
            root=root,
            mode="r",
            config_fn=self.input.wflow_toml.name,
            data_libs=self.params.data_libs,
            logger=logger,
        )

        fmt = "%Y-%m-%dT%H:%M:%S"  # wflow toml datetime format
        w.setup_config(
            **{
                "starttime": self.params.start_time.strftime(fmt),
                "endtime": self.params.end_time.strftime(fmt),
                "timestepsecs": self.params.timestep,
                "input.path_forcing": "inmaps/forcing.nc",
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

        if self.output.wflow_out_toml.is_relative_to(root):
            rel_dir = Path(os.path.relpath(root, self.output.wflow_out_toml.parent))
        else:
            rel_dir = root

        w.set_config("input.path_static", str(rel_dir / "staticmaps.nc"))

        # write to new root
        sims_root = self.output.wflow_out_toml.parent

        w.set_root(
            root=sims_root,
            mode="w+",
        )
        w.write_config(config_name=self.output.wflow_out_toml.name)
        w.write_forcing(freq_out="1Y")
