import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr
from hydromt_wflow import WflowModel

from hydroflows.methods import WflowBuild, WflowDesignHydro, WflowUpdateForcing


@pytest.fixture()
def wflow_simple_root(tmp_path):
    root = Path(tmp_path, "wflow_simple_test")

    mod = WflowModel(
        root=root,
        mode="w",
        data_libs=["artifact_data"],
    )

    region = {
        "subbasin": [12.2051, 45.8331],
        "uparea": 30,
    }

    # TODO: see if we can simplify this
    hydrography = mod.data_catalog.get_rasterdataset("merit_hydro")
    hydrography["basins"] = hydrography["basins"].astype("uint32")

    mod.setup_basemaps(
        region=region,
        hydrography_fn=hydrography,
    )

    mod.write_grid()
    mod.write_config()

    return root



def test_wflow_build(sfincs_src_points, sfincs_region_path, tmp_path):
    # write src points to file
    fn_sfincs_src_points = Path(sfincs_region_path.parent, "src.geojson")
    sfincs_src_points.to_file(fn_sfincs_src_points, driver="GeoJSON")

    input = {"sfincs_region": str(sfincs_region_path)}

    fn_wflow_toml = Path(tmp_path, "model", "wflow.toml")
    output = {"wflow_toml": str(fn_wflow_toml)}

    WflowBuild(input=input, output=output).run()

    fn_geoms = Path(fn_wflow_toml.parent, "staticgeoms", "gauges_locs.geojson")

    assert fn_wflow_toml.exists()

    assert fn_geoms.exists()


def test_wflow_update_forcing(wflow_simple_root):
    toml_fn = Path(wflow_simple_root, "wflow_sbm.toml")
    input = {"wflow_toml": str(toml_fn)}

    fn_wflow_toml_updated = Path(wflow_simple_root, "sims", "sim1", "wflow_sim1.toml")
    output = {"wflow_toml": str(fn_wflow_toml_updated)}

    WflowUpdateForcing(input=input, output=output).run()

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
