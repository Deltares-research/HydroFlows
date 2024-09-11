"""SFINCS model utility functions."""

from pathlib import Path
from typing import Dict, Literal, Optional, cast

import geopandas as gdf
from hydromt_sfincs import SfincsModel

from hydroflows.events import Event, Forcing
from hydroflows.utils.path_utils import make_relative_paths


def _check_forcing_locs(
    forcing: Forcing, sf: SfincsModel, ftype=Literal["bzs", "dis"]
) -> Optional[gdf.GeoDataFrame]:
    if forcing.locs is None and ftype in sf.forcing:
        locs = cast(gdf.GeoDataFrame, sf.forcing[ftype].vector.to_gdf())
        # find overlapping indexes
        try:
            forcing.data.columns = forcing.data.columns.map(int)
        except ValueError:
            pass
        loc_names = list(set(locs.index) & set(forcing.data.columns))
        if len(loc_names) == 0:
            raise ValueError("No overlapping locations indices found")
        locs = locs.loc[loc_names]
    else:
        locs = forcing.locs
    return locs


def parse_event_sfincs(
    root: Path, event: Event, out_root: Path, sfincs_config: Optional[Dict] = None
) -> None:
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
    dt_sec = (event.tstop - event.tstart).total_seconds()
    sf.config.update(
        {
            "tref": event.tstart.strftime(fmt),
            "tstart": event.tstart.strftime(fmt),
            "tstop": event.tstop.strftime(fmt),
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
                locs = _check_forcing_locs(forcing, sf, ftype="bzs")
                sf.setup_waterlevel_forcing(
                    timeseries=forcing.data, locations=locs, merge=False
                )
                config.update({"bzsfile": "sfincs.bzs", "bndfile": "sfincs.bnd"})

            case "discharge":
                locs = _check_forcing_locs(forcing, sf, ftype="dis")
                sf.setup_discharge_forcing(
                    timeseries=forcing.data, locations=locs, merge=False
                )
                config.update({"disfile": "sfincs.dis", "srcfile": "sfincs.src"})

            case "rainfall":
                sf.setup_precip_forcing(timeseries=forcing.data)
                config.update({"precipfile": "sfincs.precip"})

    # change root and update config
    sf.set_root(out_root, mode="w+")
    sf.setup_config(**config)
    # Write forcing and config only
    sf.write_forcing()
    sf.write_config()
