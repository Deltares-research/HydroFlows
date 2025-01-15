"""Utility for merging climate change factor datasets."""

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


def merge_climate_datasets(
    change_ds: list | tuple,
    aligned: bool = False,
    res: float = 0.25,
    quantile: float = 0.5,
) -> xr.Dataset:
    """Merge climate datasets.

    These contain monthly change factors.

    Parameters
    ----------
    change_ds : list | tuple
        List of datasets of all climate models for a certain \
scenario-horizon combination.
    aligned : bool
        Whether the datasets are already aligned or not. By default False
    res : float
        The resolution of the resulting dataset in degrees.
    quantile : float
        The quantile of the merged data to be returned. Dafault is 0.5 (median)

    Returns
    -------
    xr.Dataset
        The resulting merged dataset.
    """
    ymax, ymin, xmax, xmin = None, None, None, None
    for fname in change_ds:
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
    for fname in change_ds:
        ds = xr.open_dataset(fname, lock=False)
        if len(ds) == 0 or ds is None:
            continue
        if "time" in ds.coords:
            if ds.indexes["time"].dtype == "O":
                ds["time"] = ds.indexes["time"].to_datetimeindex()
        # Reproject to regular grid
        # drop extra dimensions for reprojection
        if not aligned:
            ds_reproj = ds.squeeze(drop=True)
            ds_reproj = ds_reproj.raster.reproject_like(ds_grid, method="nearest")
            # Re-add the extra dims
            ds_reproj = ds_reproj.expand_dims(
                {
                    "clim_project": ds["clim_project"].values,
                    "model": ds["model"].values,
                    "scenario": ds["scenario"].values,
                    "horizon": ds["horizon"].values,
                    "member": ds["member"].values,
                }
            )
            ds_list.append(ds_reproj)
            continue
        ds_list.append(ds)

    ds_out = xr.merge(ds_list)
    ds_out_stat = ds_out.quantile(quantile, dim="model").squeeze(drop=True)

    return ds_out_stat
