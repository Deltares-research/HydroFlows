from pathlib import Path

import pytest

from hydroflows.methods.hazard_validation import FloodmarksValidation


@pytest.mark.filterwarnings("ignore:::")  # ignore SettingWithCopyWarning from pandas
@pytest.mark.requires_test_data()
def test_floodmarks_validation(
    tmp_path: Path, tmp_floodmark_points: Path, hazard_map_tif: Path, region: Path
):
    out_root = Path(tmp_path / "data")

    rule = FloodmarksValidation(
        floodmarks_geom=tmp_floodmark_points,
        flood_hazard_map=hazard_map_tif,
        region=region,
        waterlevel_col="water_level_obs",
        waterlevel_unit="m",
        out_root=out_root,
        bins=[-2, -1.5, 0, 5],
        figsize=(13, 8),
        bmap="OSM",
    )

    assert (
        rule.output.validation_scores_csv
        == out_root / "validation_scores_floodmarks.csv"
    )

    rule.run_with_checks()
