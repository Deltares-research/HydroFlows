"""Climate utility functions."""

from pathlib import Path

import xarray as xr

CLIMATE_VARS = {
    "precip": {
        "resample": "sum",
        "multiplier": True,
    },
    "temp": {
        "resample": "mean",
        "multiplier": False,
    },
    "pet": {
        "resample": "sum",
        "multiplier": True,
    },
    "temp_dew": {
        "resample": "mean",
        "multiplier": False,
    },
    "kin": {
        "resample": "mean",
        "multiplier": True,
    },
    "wind": {
        "resample": "mean",
        "multiplier": True,
    },
    "tcc": {
        "resample": "mean",
        "multiplier": True,
    },
}


def intersection(lst1, lst2):
    """Get matching elements from two lists."""
    return list(set(lst1) & set(lst2))


def to_netcdf(
    obj: xr.Dataset,
    file_name: str,
    output_dir: Path | str,
):
    """Write xarray to netcdf."""
    dvars = obj.data_vars
    _ = obj.to_netcdf(
        Path(output_dir, file_name),
        encoding={k: {"zlib": True} for k in dvars},
        compute=True,
    )
