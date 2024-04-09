"""Testing for FIAT rules."""
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from hydroflows.methods import FIATBuild


# TODO move to conftest but with a different name to avoid conflicts
@pytest.fixture()
def region():
    return gpd.GeoDataFrame(
        geometry=[Polygon([
            [ -43.276990254787755, -22.947499073009226 ],
            [ -43.197418907712219, -22.936319627552329 ],
            [ -43.159934884709692, -22.921852109902233 ],
            [ -43.162236535244929, -22.898506797330484 ],
            [ -43.199062943808819, -22.886998544654269 ],
            [ -43.242794303978428, -22.911987893322621 ],
            [ -43.276990254787755, -22.927770639849999 ],
            [ -43.276990254787755, -22.947499073009226 ]
            ])
        ],
        crs="EPSG:4326",
    )


@pytest.fixture()
def region_path(tmpdir, region):
    p = Path(str(tmpdir), "region.geojson")
    region.to_file(p)
    return p


def test_fiat_build(tmpdir, region_path):
    # Setting input data
    input = {
        "region": region_path.as_posix(),
    }
    fn_fiat_cfg = Path(tmpdir, "fiat_model", "settings.toml")
    output = {
        "fiat_cfg": fn_fiat_cfg
    }

    # Setup the rule
    rule = FIATBuild(input=input, output=output)
    rule.run()

    assert fn_fiat_cfg.exists()
