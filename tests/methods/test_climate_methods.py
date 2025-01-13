from pathlib import Path

import pytest
import xarray as xr

from hydroflows.methods.climate import (
    ClimateFactorsGridded,
    ClimateStatistics,
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


@pytest.mark.requires_test_data()
def test_climate_factors(tmp_path: Path, climate_stats: list):
    method = ClimateFactorsGridded(
        hist_stats=climate_stats[0],
        fut_stats=climate_stats[1],
        model="a-model",
        scenario="a-scenario",
        horizon=[[2050, 2060]],
        data_root=Path(tmp_path),
    )
    method.run()

    file = Path(
        method.output.change_factors.as_posix().format(
            horizons=method.formatted_wildcards[0]
        ),
    )
    assert file.is_file()
    ds = xr.open_dataset(file)
    assert method.formatted_wildcards[0] in ds.horizon
    assert int(ds.precip.values.mean()) == 50
    ds = None


@pytest.mark.requires_test_data()
def test_merge_datasets(tmp_path: Path, climate_stats: list):
    method2 = MergeDatasets(
        climate_stats[1:],
        scenario="a-scenario",
        horizon="2050-2060",
        data_root=Path(tmp_path),
    )
    method2.run()

    assert method2.output.merged.is_file()
    ds = xr.open_dataset(method2.output.merged)
    assert ds.lon.size == 8
    assert int(ds.precip.values.mean()) == 40
