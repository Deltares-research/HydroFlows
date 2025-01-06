"""Functions for determining climate delta's."""

import os
from os.path import dirname, join
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import hydromt
import numpy as np
import pandas as pd
import xarray as xr
from dask.diagnostics import ProgressBar
from hydromt.workflows import forcing

# Time tuple for timeseries
CLIM_PROJECT_TIME_TUPLE = {
    "cmip6": {
        "historical": ("1950-01-01", "2014-12-31"),
        "future": ("2015-01-01", "2100-12-31"),
    },
    "cmip5": {
        "historical": ("1950-01-01", "2005-12-31"),
        "future": ("2006-01-01", "2100-12-31"),
    },
    "isimip3": {
        "historical": ("1991-01-01", "2014-12-31"),
        "future": ("2021-01-01", "2100-12-31"),
    },
}


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


def get_stats_clim_projections(
    data: xr.Dataset,
    geom: gpd.GeoDataFrame,
    clim_source: str,
    model: str,
    scenario: str,
    member: str,
    compute_pet: bool = False,
    compute_wind: bool = False,
    compute_tdew: bool = False,
    pet_method: Optional[str] = "makkink",
    save_grids: bool = False,
    time_horizon: Optional[str] = None,
    drop_vars_pet: Union[List[str], None] = None,
    drop_vars_wind: Union[List[str], None] = None,
    drop_vars_dew: Union[List[str], None] = None,
):
    """
    Extract climate projections statistics for a specific geom.

    Output is a dataset with mean monthly climate (e.g precipitation and
    temperature) timeseries averaged over the geom.

    If save_grids is True, also returns a dataset with mean monthly regime of climate
    variables (e.g. precipitation and temperature) statistics (12 maps) over the geom.
    The regimes can be computed for specific time horizons instead of the entire period
    if needed.

    Supported variables:
    * precip: precipitation [mm/month] or [mm/day]
    * temp: temperature [°C]
    * pet: potential evapotranspiration [mm/month] - can be computed using several
      methods and variables (see pet_method)
    * temp_dew: dew point temperature [°C] - can be computed using relative or specific
      humidity (see tdew_method)
    * wind: wind speed [m/s] - can be computed from u and v wind components
    * kin: incoming shortwave radiation [W/m2]
    * tcc: total cloud cover [-]

    Parameters
    ----------
    data: dataset
        dataset for all available variables after opening data catalog
    geom : gpd.GeoDataFrame
        region geometry to extract the data from before averaging over x and y dim.
    clim_source : str
        name of the climate project source (e.g. cmip5, cmip6, isimip3).
        should link to the name in the yml catalog.
    model : str
        model name of the climate model (e.g. ipsl, gfdl).
    scenario : str
        scenario name of the climate model (e.g. rcp4.5, rcp8.5).
    member : str
        member name of the climate model (e.g. r1i1p1f1).
    compute_pet : bool
        compute potential evapotranspiration. False by default.
    compute_wind : bool
        compute wind speed from u and v wind components (wind10_u and wind10_v).
        False by default.
    compute_tdew : bool
        compute dew point temperature from temperature and relative humidity.
        False by default.
    pet_method : str
        method to compute potential evapotranspiration if compute_pet is True.
        available methods are 'makkink' (default), 'debruin'.
    save_grids : bool
        save gridded stats as well as scalar stats. False by default.
    time_horizon : dict
        dictionary with time horizons to select before computing monthly regime.
        several periods can be supplied if needed. the dictionary should have the
        following format: {'period_name': ('start_year', 'end_year')}. default is None
    drop_vars_pet : list
        list of variables to drop after computing pet. default is [].
    drop_vars_wind : list
        list of variables to drop after computing wind. default is [].
    drop_vars_dew : list
        list of variables to drop after computing dew point temperature. default is [].
    """
    # get lat lon name of data
    XDIMS = ("x", "longitude", "lon", "long")
    YDIMS = ("y", "latitude", "lat")
    for dim in XDIMS:
        if dim in data.coords:
            x_dim = dim
    for dim in YDIMS:
        if dim in data.coords:
            y_dim = dim

    ds = []
    ds_scalar = []

    # Set to empty lists if none # TODO this is awful, make more efficient
    if drop_vars_pet is None:
        drop_vars_pet = []
    if drop_vars_wind is None:
        drop_vars_wind = []
    if drop_vars_dew is None:
        drop_vars_dew = []

    for var in data.data_vars:
        if var == "precip":
            var_m = data[var].resample(time="MS").sum("time")
            # for monthly cmip6 units is mm/day and not mm
            if "units" in data[var].attrs and data[var].attrs["units"] == "mm/day":
                # convert to mm/month by multiplying with number of days in month
                days_in_month = pd.to_datetime(var_m.time.values).days_in_month
                # convert days_in_month to xarray variable
                days_in_month = xr.DataArray(
                    days_in_month, dims=["time"], coords={"time": var_m.time}
                )
                var_m = var_m * days_in_month
                var_m.name = "precip"
                var_m.attrs["units"] = "mm/month"
        elif np.isin(var, ["kin", "kout", "pet"]):
            var_m = data[var].resample(time="MS").sum("time")
        else:  # for temp, wind, rh, press, tcc
            # elif "temp" in var: #for temp
            var_m = data[var].resample(time="MS").mean("time")

        # mask region before computing stats
        var_m_masked = var_m.copy()
        if var_m_masked.raster.nodata is None:
            var_m_masked.raster.set_nodata(np.nan)
        var_m_masked = var_m_masked.assign_coords(
            mask=var_m_masked.raster.geometry_mask(geom, all_touched=True)
        )
        var_m_masked = var_m_masked.raster.mask(var_m_masked.coords["mask"])
        # get scalar average over grid for each month
        var_m_scalar = var_m_masked.raster.mask_nodata().mean([x_dim, y_dim])
        ds_scalar.append(var_m_scalar.to_dataset())

        # get grid average over time for each month
        if save_grids:
            if time_horizon is not None:
                for period_name, time_tuple in time_horizon.items():
                    var_mm = var_m.sel(time=slice(*time_tuple))
                    var_mm = var_mm.groupby("time.month").mean("time")
                    # Add a new horizon dimension
                    var_mm = var_mm.expand_dims(horizon=[period_name])
                    var_mm = var_mm.transpose(..., "horizon")
                    ds.append(var_mm.to_dataset())

            # else compute stats over the whole period
            else:
                var_mm = var_m.groupby("time.month").mean("time")
                ds.append(var_mm.to_dataset())

    # mean stats over grid and time
    mean_stats_time = xr.merge(ds_scalar)

    # todo: convert press_msl to press for pet and tdew computation - need orography
    # if needed compute pet
    if compute_pet:
        timestep = mean_stats_time["time"].to_index().daysinmonth * 86400
        # need to keep press_msl for tdew computation with sh
        if compute_tdew and "sh" in mean_stats_time.data_vars:
            drop_vars_pet = [var for var in drop_vars_pet if var != "press"]
        mean_stats_time = derive_pet(
            mean_stats_time, pet_method, timestep, drop_vars=drop_vars_pet
        )
    # if needed compute wind
    if compute_wind:
        mean_stats_time = derive_wind(
            mean_stats_time, altitude=10, drop_vars=drop_vars_wind
        )
    # if needed compute dew point temperature
    if compute_tdew:
        mean_stats_time = derive_tdew(mean_stats_time, drop_vars=drop_vars_dew)

    # add coordinate on project, model, scenario, member to later merge all files
    mean_stats_time = (
        mean_stats_time.round(decimals=2)
        .assign_coords(
            {
                "clim_project": f"{clim_source}",
                "model": f"{model}",
                "scenario": f"{scenario}",
                "member": f"{member}",
            }
        )
        .expand_dims(["clim_project", "model", "scenario", "member"])
    )

    if save_grids:
        mean_stats = xr.merge(ds)
        # todo: convert press_msl to press for pet and tdew computation - need orography
        # if needed compute pet
        if compute_pet:
            timestep = xr.DataArray(
                np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]) * 86400,
                dims=["month"],
                coords={"month": mean_stats["month"]},
            )
            if compute_tdew and "sh" in mean_stats.data_vars:
                drop_vars_pet = [var for var in drop_vars_pet if var != "press"]
            mean_stats = derive_pet(
                mean_stats, pet_method, timestep, drop_vars=drop_vars_pet
            )
        # compute wind
        if compute_wind:
            mean_stats = derive_wind(mean_stats, altitude=10, drop_vars=drop_vars_wind)
        # compute dew point temperature
        if compute_tdew:
            mean_stats = derive_tdew(mean_stats, drop_vars=drop_vars_dew)

        # add coordinate on project, model, scenario, member to later merge all files
        mean_stats = (
            mean_stats.round(decimals=2)
            .assign_coords(
                {
                    "clim_project": f"{clim_source}",
                    "model": f"{model}",
                    "scenario": f"{scenario}",
                    "member": f"{member}",
                }
            )
            .expand_dims(["clim_project", "model", "scenario", "member"])
        )

    else:
        mean_stats = xr.Dataset()

    return mean_stats, mean_stats_time


def extract_climate_projections_statistics(
    region_fn: Union[str, Path],
    data_catalog: Union[str, Path],
    path_output: Union[str, Path],
    clim_source: str,
    scenario: str,
    members: List[str],
    model: str,
    variables: List[str] = ["precip", "temp"],  # noqa: B006
    pet_method: Optional[str] = "makkink",
    tdew_method: Optional[str] = "rh",
    compute_wind: bool = False,
    save_grids: bool = False,
    time_horizon: Optional[Dict[str, Tuple[str, str]]] = None,
):
    """
    Extract climate projections statistics for a specific region.

    Output is a netcdf file with mean monthly climate (e.g precipitation and
    temperature) timeseries averaged over the geom.

    If save_grids is True, also writes a netcdf file with mean monthly regime of climate
    variables (e.g. precipitation and temperature) statistics (12 maps) over the geom.
    The regimes can be computed for specific time horizons instead of the entire period
    if needed.

    Supported variables:
    * precip: precipitation [mm/month] or [mm/day]
    * temp: temperature [°C]
    * pet: potential evapotranspiration [mm/month] - can be computed using several
      methods and variables (see pet_method)
    * temp_dew: dew point temperature [°C] - can be computed using relative or specific
      humidity (see tdew_method)
    * wind: wind speed [m/s] - can be computed from u and v wind components
    * kin: incoming shortwave radiation [W/m2]
    * tcc: total cloud cover [-]

    Parameters
    ----------
    region_fn : str, Path
        Path to the region geodataframe file.
    data_catalog : str, Path
        Path to the data catalog yml file containing the climate source info.
    path_output : str, Path
        Path to the output folder.
    clim_source : str
        Name of the climate project source (e.g. cmip5, cmip6, isimip3). Should link to
        the name in the yml catalog.
        Allowed climate project sources are: [cmip5, cmip6, isimip3].
    scenario : str
        Scenario name of the climate model (e.g. historical, ssp245, ssp585).
        Depends on the climate source.
    members : list
        List of member names of the climate model (e.g. r1i1p1f1). Depends on the
        climate source.
    model : str
        Model name of the climate model (e.g. 'NOAA-GFDL_GFDL-ESM4', 'INM_INM-CM5-0').
        Depends on the climate source. For cmip6 climate source, if '_' are present in
        the model name, they will be replaced by '/' to match the data catalog entry.
    variables : list
        List of variables to extract (e.g. ['precip', 'temp']). Variables should be
        present in the climate source.
    pet_method : str
        Method to compute potential evapotranspiration. Use None to use pet from the
        climate source. Available methods are 'makkink' (default), 'debruin'.
        Required variables for each method are:

        * makkink: 'temp' [°C], 'press' [hPa], 'kin'[W/m2]
        * debruin: 'temp' [°C], 'press' [hPa], 'kin' [W/m2], 'kout' [W/m2]
    tdew_method : str
        Method to compute dewpoint temperature. Use None to use tdew from the climate
        source. Available methods are 'rh' (default), 'sh' to compute using either
        relative or specific humidity. Required variables for each method are:

        * rh: 'temp' [°C], 'rh' [%]
        * sh: 'temp' [°C], 'sh' [kg/kg], 'press' [hPa]
    compute_wind : bool
        Compute wind speed from u and v wind components (wind10_u and wind10_v). False
        by default.
    save_grids : bool
        Save gridded stats as well as scalar stats. False by default.
    time_horizon : dict
        Dictionary with time horizons to select before computing monthly regime. Several
        periods can be supplied if needed. The dictionary should have the following
        format: {'period_name': ('start_year', 'end_year')}. Default is None to select
        the entire period. If time horizon is given, an extra dimension will be added to
        the output netcdf file.
    """
    # initialize model and region properties
    geom = gpd.read_file(region_fn)
    bbox = list(geom.total_bounds)
    buffer = 1

    # initialize data_catalog from yml file
    data_catalog = hydromt.DataCatalog(data_libs=data_catalog)

    # Check climate source name and get time_tuple
    if clim_source not in CLIM_PROJECT_TIME_TUPLE.keys():
        raise ValueError(
            f"Climate source {clim_source} not supported. "
            f"Please choose from {CLIM_PROJECT_TIME_TUPLE.keys()}"
        )
    if scenario == "historical":
        time_tuple = CLIM_PROJECT_TIME_TUPLE[clim_source]["historical"]
    else:
        time_tuple = CLIM_PROJECT_TIME_TUPLE[clim_source]["future"]

    # Initialize list of variables depending on pet_method
    if "pet" in variables and pet_method is not None:
        compute_pet = True
        # Remove pet from variables
        variables.remove("pet")
        # Find if kin was in the requested variables
        if "kin" in variables:
            drop_vars_pet = ["press", "kout"]
        else:
            drop_vars_pet = ["press", "kin", "kout"]
        # Add pet variables depending on method
        if pet_method == "makkink":
            variables.extend(["press", "kin"])
        elif pet_method == "debruin":
            variables.extend(["press", "kin", "kout"])
        else:
            raise ValueError(
                f"pet_method {pet_method} not supported. "
                f"Please choose from ['makkink', 'debruin']"
            )
    else:
        compute_pet = False
        drop_vars_pet = []

    # Initialize list of variables depending on tdew_method
    if "temp_dew" in variables and tdew_method is not None:
        compute_tdew = True
        variables.remove("temp_dew")
        if tdew_method == "rh":
            if "temp" in variables:
                drop_vars_dew = ["rh"]
                variables.extend(["rh"])
            else:
                drop_vars_dew = ["rh", "temp"]
                variables.extend(["temp", "rh"])
        elif tdew_method == "sh":
            if "temp" in variables:
                drop_vars_dew = ["sh", "press"]
                variables.extend(["sh", "press"])
            else:
                drop_vars_dew = ["sh", "press", "temp"]
                variables.extend(["temp", "sh", "press"])
        else:
            raise ValueError(
                f"tdew_method {tdew_method} not supported. "
                f"Please choose from ['rh', 'sh']"
            )
    else:
        compute_tdew = False
        drop_vars_dew = []

    if "wind" in variables and compute_wind:
        variables.remove("wind")
        variables.extend(["wind10_u", "wind10_v"])

    # check if model really exists from data catalog entry
    # else skip and provide empty ds
    ds_members_mean_stats = []
    ds_members_mean_stats_time = []

    for member in members:
        print(member)
        # For cmip6, replace _ in model by \ to match the data catalog entry
        if clim_source == "cmip6":
            model_entry = model.replace("_", "/")
        else:
            model_entry = model
        entry = f"{clim_source}_{model_entry}_{scenario}_{member}"
        if entry in data_catalog:
            # bug #677 in hydromt: attrs for non selected variables
            # for now, remove and update after get_data method
            dc_entry = data_catalog[entry].to_dict()
            entry_attrs = dc_entry.pop("attrs", None)
            dc_entry.pop("data_type", None)
            adapter = hydromt.data_adapter.RasterDatasetAdapter(**dc_entry)
            data_catalog.add_source(entry, adapter)

            # Try to read all variables at once
            try:  # todo can this be replaced by if statement?
                data = data_catalog.get_rasterdataset(
                    entry,
                    bbox=bbox,
                    buffer=buffer,
                    time_tuple=time_tuple,
                    variables=variables,
                )
                # needed for cmip5/cmip6 cftime.Datetime360Day which is not picked up
                data = data.sel(time=slice(*time_tuple))
            except BaseException:
                # if it is not possible to open all variables at once,
                # loop over each one, remove duplicates and then merge:
                ds_list = []
                for var in variables:
                    try:
                        data_ = data_catalog.get_rasterdataset(
                            entry,
                            bbox=bbox,
                            buffer=buffer,
                            time_tuple=time_tuple,
                            variables=[var],
                        )
                        # drop duplicates if any
                        data_ = data_.drop_duplicates(dim="time", keep="first")
                        ds_list.append(data_)
                    except BaseException:
                        print(f"{scenario}", f"{model_entry}", f"{var} not found")
                # merge all variables back to data
                data = xr.merge(ds_list)

            # bug #677 in hydromt: attrs for non selected variables
            # update the attrs
            if entry_attrs is not None:
                # unit attributes
                for k in entry_attrs:
                    if k in data:
                        data[k].attrs.update(entry_attrs[k])

            # calculate statistics
            mean_stats, mean_stats_time = get_stats_clim_projections(
                data,
                geom,
                clim_source,
                model,
                scenario,
                member,
                compute_pet=compute_pet,
                compute_wind=compute_wind,
                compute_tdew=compute_tdew,
                pet_method=pet_method,
                save_grids=save_grids,
                time_horizon=time_horizon,
                drop_vars_pet=drop_vars_pet,
                drop_vars_wind=["wind10_u", "wind10_v"],
                drop_vars_dew=drop_vars_dew,
            )

        else:
            mean_stats = xr.Dataset()
            mean_stats_time = xr.Dataset()

        # merge members results
        ds_members_mean_stats.append(mean_stats)
        ds_members_mean_stats_time.append(mean_stats_time)

    if save_grids:
        nc_mean_stats = xr.merge(ds_members_mean_stats)
    else:
        nc_mean_stats = xr.Dataset()
    nc_mean_stats_time = xr.merge(ds_members_mean_stats_time)

    # write netcdf
    # use hydromt function instead to write to netcdf?
    dvars = nc_mean_stats_time.data_vars

    if scenario == "historical":
        name_nc_out = f"historical_stats_{model}.nc"
        name_nc_out_time = f"historical_stats_time_{model}.nc"
    else:
        name_nc_out = f"stats-{model}_{scenario}.nc"
        name_nc_out_time = f"stats_time-{model}_{scenario}.nc"

    # Create output dir (model name can contain subfolders)
    dir_output = dirname(join(path_output, name_nc_out_time))
    if not os.path.exists(dir_output):
        os.makedirs(dir_output)

    print("writing stats over time to nc")
    delayed_obj = nc_mean_stats_time.to_netcdf(
        join(path_output, name_nc_out_time),
        encoding={k: {"zlib": True} for k in dvars},
        compute=False,
    )
    with ProgressBar():
        delayed_obj.compute()

    if save_grids:
        print("writing stats over grid to nc")

        # Create output dir (model name can contain subfolders)
        dir_output = dirname(join(path_output, name_nc_out))
        if not os.path.exists(dir_output):
            os.makedirs(dir_output)

        delayed_obj = nc_mean_stats.to_netcdf(
            join(path_output, name_nc_out),
            encoding={k: {"zlib": True} for k in dvars},
            compute=False,
        )
        with ProgressBar():
            delayed_obj.compute()


if __name__ == "__main__":
    if "snakemake" in globals():
        sm = globals()["snakemake"]

        # Snakemake options
        project_dir = sm.params.project_dir
        name_clim_project = sm.params.name_clim_project
        path_output = join(project_dir, "climate_projections", name_clim_project)

        # Convert time horizons from string to tuple
        time_horizon = sm.params.time_horizon
        for key, value in time_horizon.items():
            time_horizon[key] = tuple(map(str, value.split(", ")))

        extract_climate_projections_statistics(
            region_fn=sm.input.region_fid,
            data_catalog=sm.params.yml_fid,
            path_output=path_output,
            clim_source=name_clim_project,
            scenario=sm.params.name_scenario,
            members=sm.params.name_members,
            model=sm.params.name_model,
            variables=sm.params.variables,
            pet_method=sm.params.pet_method,
            tdew_method=sm.params.tdew_method,
            compute_wind=sm.params.compute_wind,
            save_grids=sm.params.save_grids,
            time_horizon=time_horizon,
        )

    else:
        print("This script should be run from a snakemake environment")
