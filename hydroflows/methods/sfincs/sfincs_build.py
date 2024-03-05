from typing import List
from ..method import Method
from ...templates import TEMPLATE_DIR

from pydantic import BaseModel, FilePath
from pathlib import Path
from hydromt_sfincs import SfincsModel
from hydromt.config import configread


__all__ = ["SfincsBuild"]

class Input(BaseModel):
    region: FilePath

class Output(BaseModel):
    sfincs_inp: Path

class Params(BaseModel):
    # optional parameter 
    config: Path = Path(TEMPLATE_DIR, "sfincs_build.yaml")
    data_libs: List[str] = ["artifact_data"]
    res: float = 50.0


class SfincsBuild(Method):
    """
    Rule for building Sfincs
    """
    name: str = "sfincs_build"
    params: Params = Params() # optional parameters
    input: Input
    output: Output

    def run(self):
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
        # create the hydromt model
        root = self.output.sfincs_inp.parent
        sf = SfincsModel(
            root=root,
            mode='w+',
            data_libs=self.params.data_libs
        )
        # build the model
        sf.build(opt=opt)
