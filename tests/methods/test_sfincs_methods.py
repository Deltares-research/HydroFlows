from pathlib import Path

from hydroflows.methods import SfincsBuild, SfincsUpdateForcing


def test_sfincs_build(sfincs_region_path , tmp_path):
    input = {
        "region": str(sfincs_region_path)
    }

    fn_sfincs_inp = Path(tmp_path, "model", "sfincs.inp")
    output = {
        "sfincs_inp": str(fn_sfincs_inp)
    }
    params = {
        "data_libs": "artifact_data",
        "res": 50.0
    }

    SfincsBuild(input=input, output=output, params=params).run()

    assert fn_sfincs_inp.exists()

def test_sfincs_update(sfincs_test_root):
    input = {"sfincs_inp": f"{sfincs_test_root}/sfincs.inp"}

    fn_sfincs_event_inp = Path(sfincs_test_root, "scenario", "event", "sfincs.inp")
    output = {"sfincs_inp": str(fn_sfincs_event_inp)}
    params = {
        "event_file": "",
        "event_name": ""
    }

    SfincsUpdateForcing(input=input, output=output, params=params).run()

    assert fn_sfincs_event_inp.exists()
