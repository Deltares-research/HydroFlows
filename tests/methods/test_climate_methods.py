from pathlib import Path

import xarray as xr

from hydroflows.methods.climate import ClimateStatistics


def test_climate_stats(tmp_path, cmip6_catalog, region):
    method = ClimateStatistics(
        region,
        data_libs=[cmip6_catalog],
        model="NOAA-GFDL_GFDL-ESM4",
        horizon=[[2000, 2010]],
        data_root=Path(tmp_path),
    )
    method.run()

    assert method.output.stats.is_file()
    ds = xr.open_dataset(method.output.stats)
    assert "historical" in ds.horizon

    method2 = ClimateStatistics(
        region,
        data_libs=[cmip6_catalog],
        model="NOAA-GFDL_GFDL-ESM4",
        scenario="ssp585",
        horizon=[[2090, 2100]],
        data_root=Path(tmp_path),
    )
    method2.run()

    assert method2.output.stats.is_file()
    ds = xr.open_dataset(method2.output.stats)
    assert "2090-2100" in ds.horizon
