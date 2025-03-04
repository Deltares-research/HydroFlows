from pathlib import Path

import pytest
import xarray as xr

from hydroflows.methods.raster import (
    MergeGriddedDatasets,
)
from hydroflows.methods.raster.merge_utils import (
    create_regular_grid,
)


# More unit test like
def test_regular_grid():
    ds = create_regular_grid(
        bbox=[-2, -2, 2, 2],
        res=0.25,
        align=True,
    )
    assert ds.lat.size == 16
    assert ds.lon.size == 16
    assert ds.raster.crs == 4326
    assert ds.raster.bounds == (-2.0, -2.0, 2.0, 2.0)


@pytest.mark.requires_test_data()
def test_merge_gridded_datasets(tmp_path: Path, cmip6_stats: Path):
    models = ["CSIRO-ARCCSS_ACCESS-CM2", "INM_INM-CM5-0", "NOAA-GFDL_GFDL-ESM4"]
    datasets = [
        Path(cmip6_stats, "change_factor", f"change_{item}_ssp585_2090-2100.nc")
        for item in models
    ]
    rule = MergeGriddedDatasets(
        datasets=datasets,
        output_name="merged_ssp585_2090-2100.nc",
        output_dir=tmp_path,
    )
    rule.run_with_checks()

    assert rule.output.merged_dataset.is_file()
    ds = xr.open_dataset(rule.output.merged_dataset)
    assert ds.lon.size == 8
    assert int(ds["precip"].values.mean() * 100) == 98
    ds = None
