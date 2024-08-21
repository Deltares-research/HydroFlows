import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from hydroflows.methods import WflowBuild, WflowDesignHydro, WflowUpdateForcing


@pytest.mark.requires_data()
def test_wflow_build(rio_region: Path, rio_test_data: Path, tmp_path: Path):
    # required inputs
    region = rio_region.as_posix()
    wflow_root = Path(tmp_path, "wflow_model")

    # some additional params
    data_libs = rio_test_data.as_posix()
    gauges = None
    upstream_area = 10
    plot_fig = False

    rule = WflowBuild(
        region=region,
        wflow_root=wflow_root,
        data_libs=data_libs,
        gauges=gauges,
        upstream_area=upstream_area,
        plot_fig=plot_fig,
    )

    rule.run_with_checks()

    # FIXME: add params gauges, then uncomment this
    # fn_geoms = Path(fn_wflow_toml.parent, "staticgeoms", "gauges_locs.geojson")
    # assert fn_geoms.exists()


@pytest.mark.requires_data()
def test_wflow_update_forcing(
    rio_wflow_model: Path, rio_test_data: Path, tmp_path: Path
):
    # copy the wflow model to the tmp_path
    root = tmp_path / "model"
    shutil.copytree(rio_wflow_model.parent, root)
    # required inputs
    wflow_toml = Path(root, rio_wflow_model.name)
    start_time = "2020-02-01"
    end_time = "2020-02-10"

    # additional param
    data_libs = rio_test_data.as_posix()

    rule = WflowUpdateForcing(
        wflow_toml=wflow_toml,
        start_time=start_time,
        end_time=end_time,
        data_libs=data_libs,
    )

    rule.run_with_checks()


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


def test_wflow_design_hydro(time_series_nc: xr.DataArray, tmp_path: Path):
    # write time series to file
    fn_time_series_nc = Path(tmp_path, "data", "output_scalar.nc")
    os.makedirs(fn_time_series_nc.parent, exist_ok=True)
    time_series_nc.to_netcdf(fn_time_series_nc)

    # required inputs
    discharge_nc = str(fn_time_series_nc)
    event_root = Path(tmp_path, "events")

    m = WflowDesignHydro(
        discharge_nc=discharge_nc,
        event_root=event_root,
        wildcard="q_event",
    )
    assert "{q_event}" in str(m.output.event_csv)
    m.run_with_checks()
