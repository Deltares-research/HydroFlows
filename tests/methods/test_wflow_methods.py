import os
from pathlib import Path
from pytest import fixture
import geopandas as gpd
from shapely.geometry import Point
from hydroflows.methods import WflowBuild, WflowUpdateForcing
from hydromt_wflow import WflowModel
from hydromt.raster import full_from_transform
import numpy as np

@fixture
def sfincs_src_points():
    return gpd.GeoDataFrame(
        geometry=[
            Point(282937.059, 5079303.114),
        ],
        crs="EPSG:32633",
    )

def test_wflow_build(sfincs_src_points, tmp_path):
    # write region to file
    fn_sfincs_src_points = Path(tmp_path, "data", "sfincs_src_points.geojson")
    os.makedirs(fn_sfincs_src_points.parent, exist_ok=True)
    sfincs_src_points.to_file(fn_sfincs_src_points, driver="GeoJSON")
    
    input = {
        "sfincs_src_points": str(fn_sfincs_src_points)
    }
    
    fn_wflow_toml = Path(tmp_path, "model", "wflow.toml")
    output = {
        "wflow_toml": str(fn_wflow_toml)
    }

    WflowBuild(input=input, output=output).run()

    return fn_wflow_toml

@fixture
def wflow_simple_root(tmp_path):
    root = Path(tmp_path, 'wflow_simple')
    mod = WflowModel(
        root = root
    )
    transform = (0.008333333333333215, 0.0, 11.778333333333352, 0.0, -0.008333333333333266, 46.69)
    da = full_from_transform(
        transform=transform,
        shape=(106, 116),
        nodata=0,
        dtype=np.int32,
        crs=4326
    )
    mod.set_grid(
        da, 'wflow_subcatch'
    )
    mod.write_grid()
    mod.write_config()
    return root


def test_wflow_update_forcing(tpm_path, wflow_simple_root):
    toml_fn = Path(wflow_simple_root, 'wflow_sbm.toml')
    input = {
        "wflow_toml_default": toml_fn
    }

    fn_wflow_toml_updated = Path(tpm_path, "model", "simulations", "sim1", "wflow_sim1.toml")
    output = {
        "wflow_toml_updated": fn_wflow_toml_updated
    }

    params = {
        "start_time": "2010-02-01T00:00:00",
        "end_time": "2011-02-10T00:00:00",
    }

    WflowUpdateForcing(input=input, params=params, output=output).run()

    assert fn_wflow_toml_updated.exists()