import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from hydroflows.methods.discharge import FluvialDesignEvents


@pytest.fixture()
def time_series_nc() -> xr.DataArray:
    rng = np.random.default_rng(12345)
    normal = pd.DataFrame(
        rng.random(size=(365 * 100, 2)) * 100,
        index=pd.date_range(start="2020-01-01", periods=365 * 100, freq="1D"),
    )
    ext = rng.gumbel(loc=100, scale=25, size=(200, 2))  # Create extremes
    for i in range(2):
        normal.loc[normal.nlargest(200, i).index, i] = ext[:, i].reshape(-1)
    da = xr.DataArray(
        data=normal.values,
        dims=("time", "Q_gauges"),
        coords={
            "time": pd.date_range(start="2000-01-01", periods=365 * 100, freq="D"),
            "Q_gauges": ["1", "2"],
        },
        attrs=dict(_FillValue=-9999),
    )

    return da


def test_fluvial_design_events(time_series_nc: xr.DataArray, tmp_path: Path):
    # write time series to file
    fn_time_series_nc = Path(tmp_path, "data", "output_scalar.nc")
    os.makedirs(fn_time_series_nc.parent, exist_ok=True)
    time_series_nc.to_netcdf(fn_time_series_nc)

    # required inputs
    discharge_nc = str(fn_time_series_nc)
    event_root = Path(tmp_path, "events")

    m = FluvialDesignEvents(
        discharge_nc=discharge_nc,
        event_root=event_root,
        wildcard="q_event",
    )
    assert "{q_event}" in str(m.output.event_csv)
    m.run_with_checks()
