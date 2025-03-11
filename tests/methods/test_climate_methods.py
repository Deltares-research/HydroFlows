from pathlib import Path

import pytest
import xarray as xr

from hydroflows.methods.climate import (
    ClimateChangeFactors,
    MonthlyClimatology,
)


# More integration test like
@pytest.mark.requires_test_data()
def test_monthly_climatology(
    tmp_path: Path,
    cmip6_catalog: Path,
    region: Path,
):
    rule = MonthlyClimatology(
        region,
        catalog_path=cmip6_catalog,
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="historical",
        horizon=[[2000, 2010]],
        output_dir=tmp_path,
    )
    rule.run()

    assert rule.output.climatology.is_file()
    ds = xr.open_dataset(rule.output.climatology)
    assert "historical" in ds.horizon
    assert int(ds.precip.values.mean() * 100) == 377
    ds = None

    rule2 = MonthlyClimatology(
        region,
        catalog_path=cmip6_catalog,
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="ssp585",
        horizon=[[2090, 2100]],
        output_dir=tmp_path,
    )
    rule2.run()

    assert rule2.output.climatology.is_file()
    ds = xr.open_dataset(rule2.output.climatology)
    assert "2090-2100" in ds.horizon
    assert int(ds.precip.values.mean() * 100) == 381
    ds = None


@pytest.mark.requires_test_data()
def test_climate_change_factors(tmp_path: Path, cmip6_stats: Path):
    rule = ClimateChangeFactors(
        hist_climatology=cmip6_stats
        / "climatology"
        / "climatology_NOAA-GFDL_GFDL-ESM4_historical.nc",
        future_climatology=cmip6_stats
        / "climatology"
        / "climatology_NOAA-GFDL_GFDL-ESM4_ssp585_future.nc",
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="ssp585",
        horizon=[[2090, 2100]],
        output_dir=tmp_path,
    )
    rule.run()

    file = Path(
        rule.output.change_factors.as_posix().format(
            horizons=rule.formatted_wildcards[0]
        ),
    )
    assert file.is_file()
    ds = xr.open_dataset(file)
    assert rule.formatted_wildcards[0] in ds["horizon"]
    assert int(ds["precip"].values.mean() * 10000) == 10264  # 2.64 [%]
    ds = None
