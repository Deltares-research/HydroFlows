from pathlib import Path

import pytest
import xarray as xr

from hydroflows.methods.climate import (
    ClimateFactorsGridded,
    ClimateStatistics,
    DownscaleClimateDataset,
    MergeDatasets,
)
from hydroflows.methods.climate.merge_utils import (
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


# More integration test like
@pytest.mark.requires_test_data()
def test_climate_stats(
    tmp_path: Path,
    cmip6_catalog: Path,
    region: Path,
):
    rule = ClimateStatistics(
        region,
        data_libs=[cmip6_catalog],
        model="NOAA-GFDL_GFDL-ESM4",
        horizon=[[2000, 2010]],
        data_root=tmp_path,
    )
    rule.run_with_checks()

    assert rule.output.stats.is_file()
    ds = xr.open_dataset(rule.output.stats)
    assert "historical" in ds.horizon
    assert int(ds.precip.values.mean() * 100) == 377
    ds = None

    rule2 = ClimateStatistics(
        region,
        data_libs=[cmip6_catalog],
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="ssp585",
        horizon=[[2090, 2100]],
        data_root=tmp_path,
    )
    rule2.run_with_checks()

    assert rule2.output.stats.is_file()
    ds = xr.open_dataset(rule2.output.stats)
    assert "2090-2100" in ds.horizon
    assert int(ds.precip.values.mean() * 100) == 381


@pytest.mark.requires_test_data()
def test_climate_factors(tmp_path: Path, cmip6_stats: Path):
    rule = ClimateFactorsGridded(
        hist_stats=cmip6_stats / "stats" / "stats_NOAA-GFDL_GFDL-ESM4_historical.nc",
        fut_stats=cmip6_stats / "stats" / "stats_NOAA-GFDL_GFDL-ESM4_ssp585_future.nc",
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="ssp585",
        horizon=[[2090, 2100]],
        data_root=tmp_path,
    )
    rule.run_with_checks()

    file = Path(
        rule.output.change_factors.as_posix().format(
            horizons=rule.formatted_wildcards[0]
        ),
    )
    assert file.is_file()
    ds = xr.open_dataset(file)
    assert rule.formatted_wildcards[0] in ds.horizon
    assert int(ds.precip.values.mean() * 100) == 264
    ds = None


@pytest.mark.requires_test_data()
def test_downscale_climate(
    tmp_path: Path,
    cmip6_stats: list,
    wflow_cached_model: Path,
):
    rule = DownscaleClimateDataset(
        dataset=Path(
            cmip6_stats,
            "change",
            "change_NOAA-GFDL_GFDL-ESM4_ssp585_2090-2100.nc",
        ),
        ds_like=Path(wflow_cached_model, "staticmaps.nc"),
        data_root=tmp_path,
    )
    rule.run_with_checks()

    assert rule.output.downscaled.is_file()
    ds = xr.open_dataset(rule.output.downscaled)
    assert int(ds.precip.values.mean() * 100) == 102
    assert ds.latitude.size == 200


@pytest.mark.requires_test_data()
def test_merge_datasets(tmp_path: Path, cmip6_stats: Path):
    models = ["CSIRO-ARCCSS_ACCESS-CM2", "INM_INM-CM5-0", "NOAA-GFDL_GFDL-ESM4"]
    datasets = [
        Path(cmip6_stats, "change", f"change_{item}_ssp585_2090-2100.nc")
        for item in models
    ]
    rule = MergeDatasets(
        datasets=datasets,
        scenario="ssp585",
        horizon="2090-2100",
        data_root=tmp_path,
    )
    rule.run_with_checks()

    assert rule.output.merged.is_file()
    ds = xr.open_dataset(rule.output.merged)
    assert ds.lon.size == 8
    assert int(ds.precip.values.mean() * 100) == -190
