"""Functions for the pluvial design hyetographs."""
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import xarray as xr


def eva_idf(
    da: xr.DataArray,
    durations: np.ndarray = np.array([1, 2, 3, 6, 12, 24, 36, 48], dtype=int),
    distribution: str = "gumb",
    ev_type: str = "BM",
    rps: np.ndarray = np.array([2, 5, 10, 25, 50, 100]),
    **kwargs,
) -> xr.Dataset:
    """Return IDF based on EVA. From hydromt eva dev branch.

    Return a intensity-frequency-duration (IDF) table based on block
    maxima of `da`.

    Parameters
    ----------
    da : xr.DataArray
        Timeseries data, must have a regular spaced 'time' dimension.
    durations : np.ndarray
        List of durations, provided as multiply of the data time step,
        by default [1, 2, 3, 6, 12, 24, 36, 48]
    distribution : str, optional
        Short name of distribution, by default 'gumb'
    rps : np.ndarray, optional
        Array of return periods, by default [2, 5, 10, 25, 50, 100, 250, 500]
    **kwargs :
        key-word arguments passed to the :py:meth:`eva` method.

    Returns
    -------
    xr.Dataset
        IDF table
    """
    from hydromt.stats.extremes import eva
    assert np.all(
        np.diff(durations) > 0
    ), "durations should be monotonically increasing"
    dt_max = int(durations[-1])
    da_roll = da.rolling(time=dt_max).construct("duration")
    # get mean intensity for each duration and concat into single dataarray
    da1 = [da_roll.isel(duration=slice(0, d)).mean("duration") for d in durations]
    da1 = xr.concat(da1, dim="duration")
    da1["duration"] = xr.IndexVariable("duration", durations)
    # return
    if "min_dist" not in kwargs:
        kwargs.update(min_dist=dt_max)
    return eva(
        da1, ev_type=ev_type, distribution=distribution, rps=rps, **kwargs
    )

def get_hyetograph(da_idf: xr.DataArray, dt: float, length: int) -> xr.DataArray:
    """Return hyetograph.

    Return design storm hyetograph based on intensity-frequency-duration (IDF)
    table. From hydromt eva dev branch.

    The input `da_idf` can be obtained as the output of the :py:meth:`eva_idf`.
    Note: here we use the precipitation intensity and not the depth as input!
    The design hyetograph is based on the alternating block method.

    Parameters
    ----------
    da_idf : xr.DataArray
        IDF data, must contain a 'duration' dimension
    dt : float
        Time-step for output hyetograph, same time step unit as IDF duration.
    length : int
        Number of time-step intervals in design storms.

    Returns
    -------
    xr.DataArray
        Design storm hyetograph
        #TODO: add some description of the variables and dimensions...(check below)
        The design storms time dimension is relative to the peak (time=0) of time step
        dt and total length record of length.
        If using :py:meth:`eva_idf` to obtain the IDF curves, the output is stored in
        variable `return_values`.
    """
    durations = da_idf["duration"]
    assert np.all(np.diff(durations) > 0)
    assert dt >= durations[0]

    t = np.arange(0, durations[-1] + dt, dt)
    alt_order = np.append(np.arange(1, length, 2)[::-1], np.arange(0, length, 2))

    # drop 'time' dimension if present in xarray.Dataset
    if "time" in list(da_idf.dims):
        da_idf = da_idf.drop_dims("time")
    # get cummulative precip depth
    pdepth = (da_idf * durations).reset_coords(drop=True).rename({"duration": "time"})
    # interpolate to dt temporal resolution
    # load required for argsort on next line
    pstep = (pdepth.interp(time=t).fillna(0).diff("time") / dt).load()
    # FIXME make sure pstep is decreasing with time;
    pstep.data = np.take_along_axis(pstep.values, pstep.argsort(axis=0), axis=0)[::-1,:]
    # reorder using alternating blocks method
    pevent = pstep.isel(time=slice(0, length)).isel(time=alt_order)
    # set time coordinate
    t0 = int(np.ceil((length + 1) / 2))
    pevent["time"] = xr.IndexVariable("time", (t[1 : length + 1] - t0))
    pevent.attrs.update(**da_idf.attrs)
    return pevent

def get_era5_open_meteo(lat, lon, start_date:datetime, end_date:datetime, variables):
    """Return ERA5 rainfall.

    Return a df with ERA5 raifall data at specific point location.
    using an API

    Parameters
    ----------
    lat : (float)
        Latitude coordinate.
    lon : (float)
        Longitude coordinate.
    start_date : (str)
        Start date for data download
    end_date : (str)
        End date for data download
    variables : (str)
        Variable to download
    """
    base_url = r"https://archive-api.open-meteo.com/v1/archive"
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    url = f"{base_url}?latitude={lat}&longitude={lon}" \
      f"&start_date={start_date_str}&end_date={end_date_str}" \
      f"&hourly={variables}"
    response = requests.get(url)

    # Check if request was successful
    if response.status_code == 200:
        # Parse response as JSON
        data = response.json()
        # make a df
        df = pd.DataFrame(data['hourly']).set_index('time')
        df.index = pd.to_datetime(df.index)
        return df
    else:
        # If request failed, return None
        print(f"Request failed with status code {response.status_code}")
        return None
