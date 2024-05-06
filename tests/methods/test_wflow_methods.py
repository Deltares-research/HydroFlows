import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import shutil
import xarray as xr

from hydromt_wflow import WflowModel

from hydroflows.methods import WflowBuild, WflowDesignHydro, WflowUpdateForcing


def test_wflow_build(rio_region, rio_test_data, tmp_path):
    input = {"region": str(rio_region)}

    params = {
        "data_libs": [str(rio_test_data)],
        "gauges": None,
        "upstream_area": 10,
        "plot_fig": False,
    }

    fn_wflow_toml = Path(tmp_path, "model", "wflow.toml")
    output = {"wflow_toml": str(fn_wflow_toml)}

    WflowBuild(input=input, params=params, output=output).run()

    assert fn_wflow_toml.exists()

    # FIXME: add params gauges, then uncomment this
    # fn_geoms = Path(fn_wflow_toml.parent, "staticgeoms", "gauges_locs.geojson")
    # assert fn_geoms.exists()


def test_wflow_update_forcing(rio_wflow_model, rio_test_data, tmp_path):
    # copy the wflow model to the tmp_path
    root = tmp_path / "model"
    shutil.copytree(rio_wflow_model.parent, root)
    fn_wflow_toml_updated = Path(root, "sims", "sim1", "wflow_sim1.toml")

    input = {"wflow_toml": str(root / rio_wflow_model.name)}
    params = {"data_libs": [str(rio_test_data)]}
    output = {"wflow_toml": str(fn_wflow_toml_updated)}

    WflowUpdateForcing(input=input, params=params, output=output).run()

    assert fn_wflow_toml_updated.exists()

@pytest.fixture()
def time_series_nc():
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

def test_wflow_design_hydro(time_series_nc, tmp_path):
    # write time series to file
    fn_time_series_nc = Path(tmp_path, "data", "output_scalar.nc")
    os.makedirs(fn_time_series_nc.parent, exist_ok=True)
    time_series_nc.to_netcdf(fn_time_series_nc)

    input = {
        "time_series_nc": str(fn_time_series_nc)
    }

    fn_data_catalog = Path(tmp_path, "data", "catalog.yml")

    output = {
        "event_catalog": str(fn_data_catalog)
    }

    WflowDesignHydro(input=input, output=output).run()
    assert fn_data_catalog.exists()
