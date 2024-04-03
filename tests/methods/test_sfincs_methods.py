from pathlib import Path

from hydroflows.methods import SfincsBuild


def test_sfincs_build(sfincs_region_path , tmp_path):
    input = {
        "region": str(sfincs_region_path)
    }

    fn_sfincs_inp = Path(tmp_path, "model", "sfincs.inp")
    output = {
        "sfincs_inp": str(fn_sfincs_inp)
    }

    SfincsBuild(input=input, output=output).run()

    assert fn_sfincs_inp.exists()
