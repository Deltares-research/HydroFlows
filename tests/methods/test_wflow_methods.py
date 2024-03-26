import os
from pathlib import Path

import geopandas as gpd
import pytest
from hydromt_wflow import WflowModel
from shapely.geometry import Point

from hydroflows.methods import WflowBuild, WflowUpdateForcing


@pytest.fixture()
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

    input = {"sfincs_src_points": str(fn_sfincs_src_points)}

    fn_wflow_toml = Path(tmp_path, "model", "wflow.toml")
    output = {"wflow_toml": str(fn_wflow_toml)}

    WflowBuild(input=input, output=output).run()

    assert fn_wflow_toml.exists()


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


def test_wflow_update_forcing(wflow_simple_root):
    toml_fn = Path(wflow_simple_root, "wflow_sbm.toml")
    input = {"wflow_toml": str(toml_fn)}

    fn_wflow_toml_updated = Path(wflow_simple_root, "sims", "sim1", "wflow_sim1.toml")
    output = {"wflow_toml": str(fn_wflow_toml_updated)}

    WflowUpdateForcing(input=input, output=output).run()

    assert fn_wflow_toml_updated.exists()
