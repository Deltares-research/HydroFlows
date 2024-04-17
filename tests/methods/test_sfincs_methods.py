from pathlib import Path

from hydroflows.methods import SfincsBuild, SfincsUpdateForcing


def test_sfincs_build(rio_region, rio_test_data, tmp_path):
    input = {
        "region": str(rio_region)
    }

    sfincs_inp = Path(tmp_path, "model", "sfincs.inp")
    sfincs_region = Path(tmp_path, "model", "gis", "region.geojson")
    output = {
        "sfincs_inp": str(sfincs_inp),
        "sfincs_region": str(sfincs_region)
    }
    params = {
        "data_libs": str(rio_test_data),
        "res": 100.0,
        "river_upa": 10.0
    }

    SfincsBuild(input=input, output=output, params=params).run()

    assert sfincs_inp.exists()
    assert sfincs_region.exists()

def test_sfincs_update(test_data_dir, sfincs_tmp_model_root):
    input = {
        "sfincs_inp": f"{sfincs_tmp_model_root}/sfincs.inp",
        "event_catalog": str(test_data_dir/"events.yml"),
    }

    fn_sfincs_event_inp = Path(sfincs_tmp_model_root, "scenario", "event", "sfincs.inp")
    output = {"sfincs_inp": str(fn_sfincs_event_inp)}
    params = {"event_name": "p_rp050"}

    SfincsUpdateForcing(input=input, output=output, params=params).run()

    assert fn_sfincs_event_inp.is_file()
