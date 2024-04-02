"""SFINCS build methods."""
from pathlib import Path

from hydromt.config import configread
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel, FilePath

from hydroflows.methods.method import HYDROMT_CONFIG_DIR, Method
from hydroflows.utils import decompose_cli_list

__all__ = ["SfincsBuild"]

class Input(BaseModel):
    region: FilePath

class Output(BaseModel):
    sfincs_inp: Path

class Params(BaseModel):
    # optional parameter
    config: Path = Path(HYDROMT_CONFIG_DIR, "sfincs_build.yaml")
    data_libs: str = "'artifact_data'"
    res: float = 50.0


class SfincsBuild(Method):
    """Rule for building Sfincs."""

    name: str = "sfincs_build"
    params: Params
    input: Input
    output: Output

    def run(self):
        """Run the SFINCS build method."""
        # read the configuration
        opt = configread(self.params.config)
        # update placeholders in the config
        # TODO: look into templating options
        opt['setup_grid_from_region'].update(
            res = self.params.res,
            region = {'geom': str(self.input.region)}
        )
        opt['setup_mask_active'].update(
            mask=self.input.region
        )
        # Create a list from the data_libs
        data_libs = decompose_cli_list(self.params.data_libs)
        # create the hydromt model
        root = self.output.sfincs_inp.parent
        sf = SfincsModel(
            root=root,
            mode='w+',
            data_libs=data_libs
        )
        # build the model
        sf.build(opt=opt)
