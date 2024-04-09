"""SFINCS Update forcing method."""

# from datetime.datetime import strftime
from pathlib import Path

from hydromt_sfincs import SfincsModel
from pydantic import BaseModel, FilePath

from ...utils import make_relative_paths
from ...workflows.events import EventCatalog
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
        # Unpack Input, Output, Params
        root = self.input.sfincs_inp
        out_root = self.output.sfincs_inp
        event_file = self.params.event_file
        event_name = self.params.event_name

        # Fetch event from event catalog
        event_catalog = EventCatalog.from_yaml(event_file)
        event = event_catalog.get_event_data(event_name)

        # Init sfincs and update root, config
        sf = SfincsModel(
            root=root,
            mode='r',
            write_gis=False
        )
        sf.set_root(out_root, mode='w+')
        config = make_relative_paths(sf.config, root, out_root)

        config.update({
            "tstart": event.time_range[0].strftime("%Y%m%d %H%M%S"),
            "tstop": event.time_range[1].strftime("%Y%m%d %H%M%S"),
            })

        # Set forcings, config
        for forcing in event.forcings:

            df = forcing.data

            match forcing.type:

                case "water_level":
                    sf.setup_waterlevel_forcing(
                        timeseries=df,
                        merge=False,
                    )
                    config.update({"bzsfile": "sfincs.bzs"})

                case "discharge":
                    sf.setup_discharge_forcing(
                        timeseries=df,
                        merge=False,
                    )
                    config.update({"disfile": "sfincs.dis"})

                case "rainfall":
                    sf.setup_precip_forcing(
                        timeseries=df,
                        merge=False,
                    )
                    config.update({"precipfile": "sfincs.precip"})

        # Write forcing, config
        sf.write_forcing()
        sf.setup_config(config)
        sf.write_config()
