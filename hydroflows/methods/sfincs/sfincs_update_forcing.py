"""SFINCS Update forcing method."""

# from datetime.datetime import strftime
from pathlib import Path

import pandas as pd
import yaml
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel, FilePath

from ...utils import make_relative_paths
from ..method import Method

__all__ = ["SfincsUpdateForcing"]

class Input(BaseModel):
    """Input parameters."""

    sfincs_inp: FilePath

class Output(BaseModel):
    """Output parameters."""

    sfincs_inp: Path

class Params(BaseModel):
    """Parameters"""

    event_file: FilePath
    event_name: str

class SfincsUpdateForcing(Method):
    """Method for updating SFINCS forcing."""

    name: str = "sfincs_update_forcing"
    params: Params = Params()
    input: Input
    output: Output

    def run(self):
        """Run update SFINCS method."""
        root = self.input.sfincs_inp
        out_root = self.output.sfincs_inp
        event_file = self.params.event_file

        with open(event_file, 'r') as f:
            event_dict = yaml.load(f, Loader=yaml.FullLoader)
        event = event_dict[self.params.event_name]

        sf = SfincsModel(
            root=root,
            mode='r',
            write_gis=False
        )
        sf.set_root(out_root, mode='w+')
        config = make_relative_paths(sf.config, root, out_root)

        df = pd.read_csv(event['file'])
        tstart, tstop = df.index[0], df.index[-1]

        config.update({
            "tstart": tstart.strftime("%Y%m%d %H%M%S"),
            "tstop": tstop.strftime("%Y%m%d %H%M%S")
            })
        match event['type']:
            case "discharge":
                sf.setup_discharge_forcing(
                    timeseries=df,
                    merge=False
                )
                config.update({"disfile": "sfincs.dis"})
            case "precipitation":
                sf.setup_precip_forcing(
                    timeseries=df,
                    merge=False
                )
                config.update({"precipfile": "sfincs.precip"})
            case "waterlevel":
                sf.setup_waterlevel_forcing(
                    timeseries=df,
                    merge=False
                )
                config.update({"bzsfile": "sfincs.bzs"})

        sf.write_forcing()
        sf.setup_config(config)
        sf.write_config()
