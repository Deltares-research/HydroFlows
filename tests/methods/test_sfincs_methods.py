from pathlib import Path

from hydroflows.methods import SfincsBuild, SfincsPostprocess, SfincsUpdateForcing


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

def test_sfincs_postprocess(test_data_dir, sfincs_tmp_model_root):
    fn_sfincs_event_inp = Path(
        sfincs_tmp_model_root,
        "scenario",
        "event_postprocess",
        "sfincs.inp"
    )
    fn_sfincs_dep = Path(
        sfincs_tmp_model_root,
        "gis",
        "dep.tif"
    )
    fn_sfincs_inun_tif = Path(
        sfincs_tmp_model_root,
        "scenario",
        "event_postprocess",
        "event.tif"
    )

    input = {
        "sfincs_inp": str(fn_sfincs_event_inp),
        "sfincs_dep": str(fn_sfincs_dep),
    }
    output = {
        "sfincs_inun": str(fn_sfincs_inun_tif)
    }

    SfincsPostprocess(input=input, output=output).run()

    assert fn_sfincs_inun_tif.is_file()
