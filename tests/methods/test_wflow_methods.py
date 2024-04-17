import shutil
from pathlib import Path

from hydroflows.methods import WflowBuild, WflowUpdateForcing


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
