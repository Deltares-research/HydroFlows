"""SFINCS model utility functions."""

from pathlib import Path
from shutil import copy
from typing import Dict, Literal, Optional, cast

import geopandas as gdf
from hydromt_sfincs import SfincsModel
from hydromt_sfincs.sfincs_input import SfincsInput

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
    root: Path,
    event: Event,
    out_root: Path,
    sfincs_config: Optional[Dict] = None,
    copy_model: bool = False,
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
    copy_model : bool
        Toggle copying static model files, by default False.
    """
    # check if out_root is a subdirectory of root
    if sfincs_config is None:
        sfincs_config = {}
    if copy_model:
        copy_sfincs_model(src=root, dest=out_root)

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
    if out_root.is_relative_to(root) and not copy_model:
        config = make_relative_paths(sf.config, root, out_root)
    else:
        config = sf.config
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


def copy_sfincs_model(src: Path, dest: Path) -> None:
    """Copy SFINCS model files.

    Parameters
    ----------
    src : Path
        Path to source directory.
    dest : Path
        Path to destination directory.
    """
    inp = SfincsInput.from_file(src / "sfincs.inp")
    config = inp.to_dict()

    if not dest.exists():
        dest.mkdir(parents=True)

    for key, value in config.items():
        # skip dep file if subgrid file is present
        if "dep" in key and "sbgfile" in config:
            continue
        if "file" in key:
            copy(src / value, dest / value)

    copy(src / "sfincs.inp", dest / "sfincs.inp")


def get_sfincs_basemodel_root(sfincs_inp: Path) -> Path:
    """Get folder with SFINCS static files.

    Parameters
    ----------
    sfincs_inp : Path
        Path to event sfincs.inp file.

    Returns
    -------
    Path
        Path to parent directory with static files.
    """
    inp = SfincsInput.from_file(sfincs_inp)
    config = inp.to_dict()
    n = 0
    for key, value in config.items():
        if "file" in key and "../" in value:
            n = max(n, value.count("../"))

    return sfincs_inp.parents[n]
