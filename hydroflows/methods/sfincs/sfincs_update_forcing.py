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
    event_catalog: FilePath


class Output(BaseModel):
    """Output parameters."""

    sfincs_inp: Path


class Params(BaseModel):
    """Parameters"""

    event_name: str


class SfincsUpdateForcing(Method):
    """Method for updating SFINCS forcing."""

    name: str = "sfincs_update_forcing"
    params: Params
    input: Input
    output: Output

    def run(self):
        """Run update SFINCS method."""
        # Unpack Input, Output, Params
        root = self.input.sfincs_inp.parent
        event_file = self.input.event_catalog
        out_root = self.output.sfincs_inp.parent
        event_name = self.params.event_name

        # Fetch event from event catalog
        event_catalog = EventCatalog.from_yaml(event_file)
        event = event_catalog.get_event_data(event_name)

        # Init sfincs and update root, config
        sf = SfincsModel(root=root, mode="r", write_gis=False)

        # update model simulation time range
        fmt = "%Y%m%d %H%M%S"  # sfincs inp time format
        sf.config.update(
            {
                "tstart": event.time_range[0].strftime(fmt),
                "tstop": event.time_range[1].strftime(fmt),
            }
        )

        # Set forcings, update config with relative paths
        config = make_relative_paths(sf.config, root, out_root)
        for forcing in event.forcings:
            match forcing.type:

                case "water_level":
                    sf.setup_waterlevel_forcing(
                        timeseries=forcing.data,
                        merge=False,
                    )
                    config.update({"bzsfile": "sfincs.bzs"})

                case "discharge":
                    sf.setup_discharge_forcing(
                        timeseries=forcing.data,
                        merge=False,
                    )
                    config.update({"disfile": "sfincs.dis"})

                case "rainfall":
                    sf.setup_precip_forcing(
                        timeseries=forcing.data,
                    )
                    config.update({"precipfile": "sfincs.precip"})

        # change root and update config
        sf.set_root(out_root, mode="w+")
        sf.setup_config(**config)
        # Write forcing and config only
        sf.write_forcing()
        sf.write_config()
