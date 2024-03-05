import os
from pathlib import Path
from pytest import fixture
import geopandas as gpd
from shapely.geometry import Point
from hydroflows.rules import WflowBuild

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

    assert fn_wflow_toml.exists()