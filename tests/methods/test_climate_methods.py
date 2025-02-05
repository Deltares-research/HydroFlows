from pathlib import Path

import pytest
import xarray as xr

from hydroflows.methods.climate import (
    ClimateChangeFactors,
    DownscaleClimateDataset,
    MergeGriddedDatasets,
    MonthlyClimatolgy,
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
def test_monthly_climatology(
    tmp_path: Path,
    cmip6_catalog: Path,
    region: Path,
):
    rule = MonthlyClimatolgy(
        region,
        catalog_path=cmip6_catalog,
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="historical",
        horizon=[[2000, 2010]],
        output_dir=tmp_path,
    )
    rule.run_with_checks()

    assert rule.output.climatology.is_file()
    ds = xr.open_dataset(rule.output.climatology)
    assert "historical" in ds.horizon
    assert int(ds.precip.values.mean() * 100) == 377
    ds = None

    rule2 = MonthlyClimatolgy(
        region,
        catalog_path=cmip6_catalog,
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="ssp585",
        horizon=[[2090, 2100]],
        output_dir=tmp_path,
    )
    rule2.run_with_checks()

    assert rule2.output.climatology.is_file()
    ds = xr.open_dataset(rule2.output.climatology)
    assert "2090-2100" in ds.horizon
    assert int(ds.precip.values.mean() * 100) == 381
    ds = None


@pytest.mark.requires_test_data()
def test_climate_change_factors(tmp_path: Path, cmip6_stats: Path):
    rule = ClimateChangeFactors(
        hist_climatology=cmip6_stats
        / "stats"
        / "stats_NOAA-GFDL_GFDL-ESM4_historical.nc",
        future_climatology=cmip6_stats
        / "stats"
        / "stats_NOAA-GFDL_GFDL-ESM4_ssp585_future.nc",
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="ssp585",
        horizon=[[2090, 2100]],
        output_dir=tmp_path,
    )
    rule.run_with_checks()

    file = Path(
        rule.output.change_factors.as_posix().format(
            horizons=rule.formatted_wildcards[0]
        ),
    )
    assert file.is_file()
    ds = xr.open_dataset(file)
    assert rule.formatted_wildcards[0] in ds["horizon"]
    assert int(ds["precip"].values.mean() * 100) == 264  # 2.64 [%]
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
        target_grid=Path(wflow_cached_model, "staticmaps.nc"),
        output_dir=tmp_path,
    )
    rule.run_with_checks()

    assert rule.output.downscaled.is_file()
    ds = xr.open_dataset(rule.output.downscaled)
    assert int(ds["precip"].values.mean() * 100) == 102
    assert ds["latitude"].size == 200
    ds = None


@pytest.mark.requires_test_data()
def test_merge_gridded_datasets(tmp_path: Path, cmip6_stats: Path):
    models = ["CSIRO-ARCCSS_ACCESS-CM2", "INM_INM-CM5-0", "NOAA-GFDL_GFDL-ESM4"]
    datasets = [
        Path(cmip6_stats, "change", f"change_{item}_ssp585_2090-2100.nc")
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
    assert int(ds["precip"].values.mean() * 100) == -190
    ds = None
