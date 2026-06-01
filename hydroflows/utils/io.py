"""Some I/O methods."""

from logging import getLogger
from pathlib import Path

import xarray as xr
from dask.diagnostics import ProgressBar

logger = getLogger(__name__)


def to_netcdf(
    obj: xr.Dataset,
    file_name: str,
    output_dir: Path | str,
):
    """Write xarray to netcdf."""
    dvars = obj.data_vars
    obj_compute = obj.to_netcdf(
        Path(output_dir, file_name),
        encoding={k: {"zlib": True} for k in dvars},
        compute=False,
    )

    logger.info(f"Writing {file_name}")
    with ProgressBar():
        obj_compute.compute()
