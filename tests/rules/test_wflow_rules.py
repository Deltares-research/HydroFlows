import os
from pathlib import Path
from pytest import fixture
import geopandas as gpd
from shapely.geometry import Point
from HydroFlows.rules import WflowBuild

@fixture
def sfincs_boundaries():
    return gpd.GeoDataFrame(
        geometry=[
            Point(282937.059, 5079303.114),
        ],
        crs="EPSG:32633",
    )

def test_wflow_build(sfincs_boundaries, tmp_path):
    # write region to file
    fn_sfincs_boundaries = Path(tmp_path, "data", "sfincs_boundaries.geojson")
    os.makedirs(fn_sfincs_boundaries.parent, exist_ok=True)
    sfincs_boundaries.to_file(fn_sfincs_boundaries, driver="GeoJSON")
    
    input = {
        "sfincs_boundaries": str(fn_sfincs_boundaries)
    }
    
    fn_wflow_inp = Path(tmp_path, "model", "wflow.inp")
    output = {
        "wflow_inp": str(fn_wflow_inp)
    }

    WflowBuild(input=input, output=output).run()

    assert fn_wflow_inp.exists()