"""Meteorological utility functions."""

from typing import List, Union

import numpy as np
import xarray as xr
from hydromt.workflows import forcing


def derive_pet(
    ds: xr.Dataset,
    pet_method: str,
    timestep: np.ndarray,
    drop_vars: Union[List, None] = None,
):
    """
    Compute potential evapotranspiration using different methods.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset with temperature, pressure, and radiation data.
    pet_method : str
        Method to compute potential evapotranspiration. Available methods are 'makkink',
        'debruin'.
    timestep : np.ndarray
        Timestep in seconds for each month.
    drop_vars : list
        List of variables to drop after computing pet. Default is None.

    Returns
    -------
    xr.Dataset
        Dataset with added potential evapotranspiration data.
    """
    if "press_msl" in ds:
        # todo downscale with orography
        ds = ds.rename({"press_msl": "press"})
    if pet_method == "makkink":
        ds["pet"] = forcing.pet_makkink(
            temp=ds["temp"],
            press=ds["press"],
            k_in=ds["kin"],
            timestep=timestep,
        )
    elif pet_method == "debruin":
        ds["pet"] = forcing.pet_debruin(
            temp=ds["temp"],
            press=ds["press"],
            k_in=ds["kin"],
            k_ext=ds["kout"],
            timestep=timestep,
        )
    # Drop variables
    if drop_vars is None:
        drop_vars = []
    for var in drop_vars:
        if var in ds:
            ds = ds.drop_vars(var)

    return ds


def derive_wind(
    ds: xr.Dataset,
    altitude: float = 10,
    drop_vars: Union[List, None] = None,
):
    """
    Compute wind speed from u and v wind components.

    Adjust wind speed data obtained from instruments placed at elevations other
    than the standard height of 2 m, using a logarithmic wind speed
    profile (Allen et al., 1998)

    Parameters
    ----------
    ds : xr.Dataset
        Dataset with either wind or u and v wind components data.
    altitude : float
        Altitude to correct wind speed from 10m to 2m. Default is 10m.
    drop_vars : list
        Drop u and v wind components after computing wind speed.

    Returns
    -------
    xr.Dataset
        Dataset with added wind speed data.
    """
    if "wind10_u" in ds and "wind10_v" in ds:
        ds["wind"] = np.sqrt(np.power(ds["wind10_u"], 2) + np.power(ds["wind10_v"], 2))
    else:
        print("u and v wind components not found, wind speed not computed")
    # Correct altitude from 10m to 2m wind
    ds["wind"] = ds["wind"] * (4.87 / np.log((67.8 * altitude) - 5.42))
    # Drop variables
    if drop_vars is None:
        drop_vars = []
    for var in drop_vars:
        if var in ds:
            ds = ds.drop_vars(var)

    return ds


def derive_tdew(
    ds: xr.Dataset,
    drop_vars: Union[List, None] = None,
):
    """
    Compute dew point temperature.

    Dewpoint temperature can either be computed from:

    * temperature [Celsius] and relative humidity [%] using Magnus formula and constant
      from NOAA (Bolton 1980).
    * temperature [Celsius], pressure [hPa] and specific humidity [kg/kg] using mixing ratio
      and actual vapor pressure (WMO, 2020).

    Bolton, D., 1980: The computation of equivalent potential temperature. \
Mon. Wea. Rev., 108, 1046-1053, doi:10.1175/1520-0493(1980)108%3C1046:TCOEPT%3E2.0.CO;2.
    WMO, 2020: Guide to Meteorological Instruments and Methods of \
Observation, Volume 1: Measurement of Meteorological Variables. WMO No.8.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset with climate data.
        Required variable using relative humidity: 'temp' [Celsius], 'rh' [%].
        Required variable using specific humidity: 'temp' [Celsius], 'sh' [kg/kg],
        'press' [hPa].
    drop_vars : List
        Drop humidity, pressure and/or temperature after computing dewpoint temperature.

    Returns
    -------
    xr.Dataset
        Dataset with added dew point temperature data.
    """
    if "temp" not in ds:
        print("temp not found, dew point temperature not computed")
        return ds
    if "rh" in ds:
        # Compute saturation vapor pressure in hPa
        es = 6.112 * np.exp((17.67 * ds["temp"]) / (ds["temp"] + 243.5))
        # Compute actual vapor pressure in hPa
        e = (ds["rh"] / 100) * es
    elif "sh" in ds and "press" in ds:
        # Compute mixing ratio from specific humidity (sh) in kg/kg
        m = (ds["sh"]) / (1 - ds["sh"])
        # Compute actual vapor pressure from specific humidity in hPa
        # 0.622 is epsilon: the ratio of the molecular weight of water vapor to dry air
        e = (m * ds["press"]) / (0.622 + (1 - 0.622) * m)
    else:
        print("rh or sh not found, dew point temperature not computed")
        return ds

    # Compute dew point temperature in Celsius
    ds["temp_dew"] = (243.5 * np.log(e / 6.112)) / (17.67 - np.log(e / 6.112))

    # Drop variables
    if drop_vars is None:
        drop_vars = []
    for var in drop_vars:
        if var in ds:
            ds = ds.drop_vars(var)

    return ds
