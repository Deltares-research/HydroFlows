"""SFINCS Update forcing method."""

# from datetime.datetime import strftime
from pathlib import Path
from typing import Dict

import geopandas as gpd
import numpy as np
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel

from hydroflows.events import Event
from hydroflows.methods.method import Method
from hydroflows.utils import make_relative_paths

__all__ = ["SfincsUpdateForcing"]


def parse_event_sfincs(
    root: Path,
    event: Event,
    out_root: Path,
    sfincs_config: Dict = None,
    bnd_locs: gpd.GeoDataFrame = None,
):
    """Parse event and update SFINCS model with event forcing.

    This method requires that the out_root is a subdirectory of the root directory.

    Parameters
    ----------
    root : Path
        The path to the SFINCS model configuration (inp) file.
    event : Event
        The event object containing the event description.
    out_root : Path
        The path to the output directory where the updated SFINCS model will be saved.
    sfincs_config : dict, optional
        The SFINCS simulation config settings to update sfincs_inp, by default {}.
    """
    # check if out_root is a subdirectory of root
    if sfincs_config is None:
        sfincs_config = {}
    if not out_root.is_relative_to(root):
        raise ValueError("out_root should be a subdirectory of root")

    # Init sfincs and update root, config
    sf = SfincsModel(root=root, mode="r", write_gis=False)

    # get event time range
    event.read_forcing_data()

    # update model simulation time range
    fmt = "%Y%m%d %H%M%S"  # sfincs inp time format
    dt_sec = (event.time_range[1] - event.time_range[0]).total_seconds()
    sf.config.update(
        {
            "tref": event.time_range[0].strftime(fmt),
            "tstart": event.time_range[0].strftime(fmt),
            "tstop": event.time_range[1].strftime(fmt),
            "dtout": dt_sec,  # save only single output
            "dtmaxout": dt_sec,
        }
    )
    if sfincs_config:
        sf.config.update(sfincs_config)

    # Set forcings, update config with relative paths
    config = make_relative_paths(sf.config, root, out_root)
    for forcing in event.forcings:
        match forcing.type:
            case "water_level":
                if bnd_locs is None:
                    raise ValueError(
                        "No bnd locations provided for waterlevel timeseries."
                    )
                sf.setup_waterlevel_forcing(
                    timeseries=forcing.data,
                    locations=bnd_locs,
                    merge=False,
                )
                config.update({"bzsfile": "sfincs.bzs"})
                config.update({"bndfile": "sfincs.bnd"})

            case "discharge":
                all_locs = sf.forcing["dis"].vector.to_gdf()
                # find overlapping indexes
                locs = all_locs.loc[np.int64(forcing.data.columns)]
                sf.setup_discharge_forcing(
                    timeseries=forcing.data, merge=False, locations=locs
                )
                config.update({"disfile": "sfincs.dis"})
                config.update({"srcfile": "sfincs.src"})

            case "rainfall":
                # if rainfall occurs, a stability issue in SFINCS makes sfincs crash when the courant condition is
                # set to (default) 0.5. Therefore set to 0.1
                sf.setup_config(alpha=0.1)
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


class Input(BaseModel):
    """Input parameters for the :py:class:`SfincsUpdateForcing` method."""

    sfincs_inp: Path
    """The file path to the SFINCS basemodel configuration file (inp)."""

    event_yaml: Path
    """The path to the event description file,
    see also :py:class:`hydroflows.workflows.events.Event`."""


class Output(BaseModel):
    """Output parameters for :py:class:`SfincsUpdateForcing` method."""

    sfincs_out_inp: Path
    """The path to the updated SFINCS configuration (inp) file per event."""


class Params(BaseModel):
    """Parameters for the :py:class:`SfincsUpdateForcing` method."""

    sfincs_config: Dict = {}
    """SFINCS simulation config settings to update sfincs_inp."""

    bnd_locations: Path = None
    """Path to file describing sfincs bnd locations"""


class SfincsUpdateForcing(Method):
    """Rule for updating Sfincs forcing with data from an event catalog.

    This class utilizes the :py:class:`Params <hydroflows.methods.sfincs.sfincs_update_forcing.Params>`,
    :py:class:`Input <hydroflows.methods.sfincs.sfincs_update_forcing.Input>`, and
    :py:class:`Output <hydroflows.methods.sfincs.sfincs_update_forcing.Output>` classes to run
    the postprocessing from the Sfincs netcdf to generate an inundation map.
    """

    name: str = "sfincs_update_forcing"

    def __init__(self, sfincs_inp: Path, event_yaml: Path, **params):
        """Create and validate a SfincsUpdateForcing instance.

        SFINCS simulations are stored in a simulations/{event_name} subdirectory of the basemodel.

        Parameters
        ----------
        sfincs_inp : Path
            The file path to the SFINCS basemodel configuration file (inp).
        event_yaml : Path
            The path to the event description file,
        **params
            Additional parameters to pass to the SfincsUpdateForcing instance.
            See :py:class:`sfincs_update_forcing Params <hydroflows.methods.sfincs.sfincs_update_forcing.Params>`.

        See Also
        --------
        :py:class:`sfincs_update_forcing Input <hydroflows.methods.sfincs.sfincs_update_forcing.Input>`
        :py:class:`sfincs_update_forcing Output <hydroflows.methods.sfincs.sfincs_update_forcing.Output>`
        :py:class:`sfincs_update_forcing Params <hydroflows.methods.sfincs.sfincs_update_forcing.Params>`
        """
        self.params: Params = Params(**params)
        self.input: Input = Input(sfincs_inp=sfincs_inp, event_yaml=event_yaml)

        # NOTE: event name is the stem of the event file
        event_name = self.input.event_yaml.stem
        sfincs_out_inp = (
            self.input.sfincs_inp.parent / "simulations" / event_name / "sfincs.inp"
        )
        self.output: Output = Output(sfincs_out_inp=sfincs_out_inp)

    def run(self):
        """Run the SfincsUpdateForcing method."""
        # check if the input files and the output directory exist
        self.check_input_output_paths()

        # fetch event from event yaml file
        event: Event = Event.from_yaml(self.input.event_yaml)
        event_name = self.input.event_yaml.stem
        if event_name != event.name:
            raise ValueError(
                f"Event file name {self.input.event_yaml} does not match event name {event.name}"
            )

        # update sfincs model with event forcing
        root = self.input.sfincs_inp.parent
        out_root = self.output.sfincs_out_inp.parent
        bnd_locs = None
        if self.params.bnd_locations is not None:
            bnd_locs = gpd.read_file(self.params.bnd_locations)
        parse_event_sfincs(
            root,
            event,
            out_root,
            sfincs_config=self.params.sfincs_config,
            bnd_locs=bnd_locs,
        )
