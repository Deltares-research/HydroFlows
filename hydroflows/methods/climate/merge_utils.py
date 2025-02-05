"""Utility for reducing multiple datasets using a quantile."""

from pathlib import Path
from typing import List

import numpy as np
import xarray as xr
from hydromt import raster


def create_regular_grid(
    bbox: List[float], res: float, align: bool = True
) -> xr.Dataset:
    """
    Create a regular grid based on bounding box and resolution.

    Taken from hydromt.GridModel.setup_grid.
    Replace by HydroMT function when it will be moved to a workflow.
    """
    xmin, ymin, xmax, ymax = bbox

    # align to res
    if align:
        xmin = round(xmin / res) * res
        ymin = round(ymin / res) * res
        xmax = round(xmax / res) * res
        ymax = round(ymax / res) * res
    xcoords = np.linspace(
        xmin + res / 2,
        xmax - res / 2,
        num=round((xmax - xmin) / res),
        endpoint=True,
    )
    ycoords = np.flip(
        np.linspace(
            ymin + res / 2,
            ymax - res / 2,
            num=round((ymax - ymin) / res),
            endpoint=True,
        )
    )
    coords = {"lat": ycoords, "lon": xcoords}
    grid = raster.full(
        coords=coords,
        nodata=1,
        dtype=np.uint8,
        name="mask",
        attrs={},
        crs=4326,
        lazy=False,
    )
    grid = grid.to_dataset()

    return grid


def merge_raster_datasets(
    datasets: list[Path],
    reduce_dim: str = "model",
    quantile: float = 0.5,
    aligned: bool = False,
    res: float = 0.25,
) -> xr.Dataset:
    """Merge raster datasets.

    Parameters
    ----------
    datasets : list[Path],
        List of dataset paths to raster netcdf datasets to merge
    reduce_dim : str
        The dimension to reduce the datasets along. Default is "model"
        This dimension will be added if not present in the datasets.
    quantile : float
        The quantile of the merged data to be returned. Default is 0.5 (median)
    aligned : bool
        Whether the datasets are already aligned or not. By default False
    res : float
        The resolution of the resulting dataset in degrees.

    Returns
    -------
    xr.Dataset
        The resulting merged dataset.
    """
    ymax, ymin, xmax, xmin = None, None, None, None
    for fname in datasets:
        ds = xr.open_dataset(fname, lock=False)
        if len(ds) == 0 or ds is None:
            continue
        lats = ds[ds.raster.y_dim].values
        lons = ds[ds.raster.x_dim].values
        ymin = min(ymin, np.min(lats)) if ymin is not None else np.min(lats)
        ymax = max(ymax, np.max(lats)) if ymax is not None else np.max(lats)
        xmin = min(xmin, np.min(lons)) if xmin is not None else np.min(lons)
        xmax = max(xmax, np.max(lons)) if xmax is not None else np.max(lons)
        ds.close()

    ds_grid = create_regular_grid(bbox=[xmin, ymin, xmax, ymax], res=res, align=True)

    ds_list = []
    for fname in datasets:
        ds = xr.open_dataset(fname, lock=False)
        if len(ds) == 0 or ds is None:
            continue
        if "time" in ds.coords:
            if ds.indexes["time"].dtype == "O":
                ds["time"] = ds.indexes["time"].to_datetimeindex()
        # Reproject to regular grid
        # drop extra dimensions for reprojection
        if not aligned:
            ds_reproj = ds.squeeze(
                drop=True
            ).raster.mask_nodata()  # drop extra dims and set nodata to nan
            ds_reproj = ds_reproj.raster.reproject_like(ds_grid, method="nearest")
            # Re-add the extra dims
            ds_reproj = ds_reproj.expand_dims(
                **{dim: ds.coords[dim] for dim in ds.dims if dim not in ds_reproj.dims}
            )
            if reduce_dim not in ds_reproj.dims:
                ds_reproj = ds_reproj.expand_dims(reduce_dim)
            ds_list.append(ds_reproj)
            continue
        ds_list.append(ds)

    ds_out = xr.merge(ds_list)
    ds_out_stat = ds_out.quantile(quantile, dim=reduce_dim).squeeze(drop=True)
    ds_out_stat.raster.set_crs(ds_grid.raster.crs)

    return ds_out_stat
