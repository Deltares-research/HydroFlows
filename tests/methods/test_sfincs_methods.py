import os
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from hydroflows.methods import SfincsBuild


@pytest.fixture()
def region():
    return gpd.GeoDataFrame(
        geometry=[Polygon([
            [ 318650.0, 5040000.0 ],
            [ 316221.0, 5044767.0 ],
            [ 327359.0, 5050442.0 ],
            [ 329788.0, 5045675.0 ],
            [ 318650.0, 5040000.0 ]
        ])],
        crs="EPSG:32633",
    )


def test_sfincs_build(region, tmp_path):
    # write region to file
    fn_region = Path(tmp_path, "data", "region.geojson")
    os.makedirs(fn_region.parent, exist_ok=True)
    region.to_file(fn_region, driver="GeoJSON")
    input = {
        "region": str(fn_region)
    }

    fn_sfincs_inp = Path(tmp_path, "model", "sfincs.inp")
    output = {
        "sfincs_inp": str(fn_sfincs_inp)
    }

    SfincsBuild(input=input, output=output).run()

    assert fn_sfincs_inp.exists()
