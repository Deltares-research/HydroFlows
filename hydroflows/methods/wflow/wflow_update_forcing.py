"""Wflow update forcing method."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from hydromt.log import setuplog
from hydromt_wflow import WflowModel

from hydroflows._typing import FolderPath, ListOfStr, OutPath
from hydroflows.methods.wflow.wflow_utils import copy_wflow_model, shift_time
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["WflowUpdateForcing"]


class Input(Parameters):
    """Input parameters for the :py:class:`WflowUpdateForcing` method."""

    wflow_toml: FolderPath
    """The file path to the Wflow (toml) configuration file from the initial
    Wflow model to be updated."""

    catalog_path: Optional[Path] = None
    """The file path to the data catalog. This is a file in yml format, which should contain the data sources for precipitation,
    temperature, elevation grid of the climate data (optionally) and
    potential evaporation (PET) estimation."""


class Output(Parameters):
    """Output parameters for the :py:class:`WflowUpdateForcing` method."""

    wflow_out_toml: FolderPath
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

    output_dir: OutPath
    """Output location relative to the workflow root. The updated model will be stored in <output_dir>."""

    copy_model: bool = False
    """Create full copy of model or create rel paths in model config."""

    timestep: int = 86400  # in seconds
    """The timestep for generated forcing in seconds."""

    predefined_catalogs: Optional[ListOfStr] = None
    """List of predefined data catalogs containing the data sources specified in the config file."""

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

    _test_kwargs = {
        "wflow_toml": Path("wflow.toml"),
        "catalog_path": Path("data_catalog.yml"),
        "start_time": datetime(1990, 1, 1),
        "end_time": datetime(1990, 1, 2),
        "output_dir": "simulations",
    }

    def __init__(
        self,
        wflow_toml: Path,
        start_time: datetime,
        end_time: datetime,
        output_dir: str,
        catalog_path: Optional[Path] = None,
        predefined_catalogs: Optional[ListOfStr] = None,
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
        end_time : datetime
            The end time of the period for which we want to generate forcing
        output_dir : str
            Output location of updated model
        catalog_path: Optional[Path], optional
            The path to the data catalog file (.yml) that contains the data sources
            specified in the config file. If None (default), a predefined data catalog should be provided.
        predefined_catalogs : Optional[ListOfStr], optional
            A list containing the predefined data catalog names.
        **params
            Additional parameters to pass to the WflowUpdateForcing instance.
            See :py:class:`wflow_update_forcing Params <hydroflows.methods.wflow.wflow_update_forcing.Params>`.

        See Also
        --------
        :py:class:`wflow_update_forcing Input <hydroflows.methods.wflow.wflow_update_forcing.Input>`
        :py:class:`wflow_update_forcing Output <hydroflows.methods.wflow.wflow_update_forcing.Output>`
        :py:class:`wflow_update_forcing Params <hydroflows.methods.wflow.wflow_update_forcing.Params>`
        :py:class:`hydromt_wflow.WflowModel`
        """
        self.params: Params = Params(
            start_time=start_time,
            end_time=end_time,
            output_dir=output_dir,
            predefined_catalogs=predefined_catalogs,
            **params,
        )
        self.input: Input = Input(wflow_toml=wflow_toml, catalog_path=catalog_path)
        if not self.input.catalog_path and not self.params.predefined_catalogs:
            raise ValueError(
                "A data catalog must be specified either via catalog_path or predefined_catalogs."
            )
        wflow_out_toml = self.params.output_dir / "wflow_sbm.toml"
        if not self.params.copy_model and not self.params.output_dir.is_relative_to(
            self.input.wflow_toml.parent
        ):
            raise ValueError(
                "Output directory must be relative to input directory when not copying model."
            )

        self.output: Output = Output(wflow_out_toml=wflow_out_toml)

    def _run(self):
        """Run the WflowUpdateForcing method."""
        logger = setuplog("update", log_level=20)

        root = self.input.wflow_toml.parent
        sims_root = self.output.wflow_out_toml.parent

        data_libs = []
        if self.params.predefined_catalogs:
            data_libs += self.params.predefined_catalogs
        if self.input.catalog_path:
            data_libs += [self.input.catalog_path]
        if self.params.copy_model:
            copy_wflow_model(src=root, dest=sims_root)

        w = WflowModel(
            root=root,
            mode="r",
            config_fn=self.input.wflow_toml.name,
            data_libs=data_libs,
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
            chunksize=100,
        )

        if self.params.copy_model:
            rel_dir = Path(".")
        else:
            rel_dir = Path(os.path.relpath(root, self.output.wflow_out_toml.parent))

        w.set_config("input.path_static", str(rel_dir / "staticmaps.nc"))

        w.set_root(
            root=sims_root,
            mode="w+",
        )
        w.write_config(config_name=self.output.wflow_out_toml.name)
        w.write_forcing(freq_out="3M")

        # Shift the starttime back by one timestep and re-write config
        w.set_config(
            "starttime",
            shift_time(
                w.get_config("starttime"),
                delta=-w.get_config("timestepsecs"),
                units="seconds",
            ),
        )

        # Make sure files paths as posix, write_forcing() doesn't do this correctly.
        posix_paths = {
            "input.path_forcing": Path(w.config["input"]["path_forcing"]).as_posix(),
            "input.path_static": Path(w.config["input"]["path_static"]).as_posix(),
        }
        w.setup_config(**posix_paths)
        w.write_config(config_name=self.output.wflow_out_toml.name)
