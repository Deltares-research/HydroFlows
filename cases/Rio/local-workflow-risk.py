"""Script to generate workflow files for the Rio case flood risk assessment using local data."""

# %%
# Import packages
import os
from pathlib import Path

from hydroflows import Workflow
from hydroflows.log import setuplog
from hydroflows.methods.fiat import (
    FIATBuild,
    FIATRun,
    FIATUpdateHazard,
)
from hydroflows.methods.rainfall import FutureClimateRainfall, PluvialDesignEvents
from hydroflows.methods.script import ScriptMethod
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsDownscale,
    SfincsPostprocess,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.workflow.workflow_config import WorkflowConfig

# Where the current file is located
pwd = Path(__file__).parent

# %%
# General setup of workflow
# Define variables
name = "local"
setup_root = Path(pwd, "setups", name)
# Create the case directory
setup_root.mkdir(exist_ok=True, parents=True)
os.chdir(setup_root)
# Setup the log file
setuplog(path=setup_root / "hydroflows.log", level="DEBUG")

# %%
# Setup the config file and data libs
# Config
config = WorkflowConfig(
    # general settings
    region=Path(pwd, "data/region.geojson"),
    plot_fig=True,
    # sfincs settings
    hydromt_sfincs_config=Path(setup_root, "hydromt_config/sfincs_config.yml"),
    sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
    sfincs_res=50,
    river_upa=10,
    depth_min=0.05,
    # fiat settings
    hydromt_fiat_config=Path(setup_root, "hydromt_config/fiat_config.yml"),
    fiat_exe=Path(pwd, "bin/fiat_v0.2.0/fiat.exe"),
    continent="South America",
    risk=True,
    # design events settings
    rps=[5, 10, 25],
    start_date="1990-01-01",
    end_date="2023-12-31",
)

# Data libs (outside config as we will append the preprocessed dc)
data_libs = (
    [
        Path(pwd, "data/local-data/data_catalog.yml"),  # local data catalog
        Path(pwd, "data/global-data/data_catalog.yml"),  # global data catalog
    ],
)

# %%
# Setup the workflow
w = Workflow(
    config=config,
    name=name,
    root=setup_root,
    wildcards={"future_climate_dT": ["0.9", "1.2", "1.8"]},
)

# %%
# Sfincs build
sfincs_build = SfincsBuild(
    region=w.get_ref("$config.region"),
    sfincs_root="models/sfincs",
    default_config=w.get_ref("$config.hydromt_sfincs_config"),
    data_libs=data_libs,
    res=w.get_ref("$config.sfincs_res"),
    river_upa=w.get_ref("$config.river_upa"),
    plot_fig=w.get_ref("$config.plot_fig"),
)
w.add_rule(sfincs_build, rule_id="sfincs_build")

# %%
# Preprocess local FIAT data scripts (clip exposure & preprocess clipped exposure)

# Clip exposure datasets to the region of interest.
fiat_clip_exp = ScriptMethod(
    script=Path(pwd, "scripts", "clip_exposure.py"),
    # Note that the output paths/names are hardcoded in the scipt
    # the same applies to the data catalog
    output={
        "census": Path(pwd, "data/preprocessed-data/census20102.gpkg"),
        "building_footprints": Path(
            pwd, "data/preprocessed-data/building_footprints.gpkg"
        ),
        "building_centroids": Path(
            pwd, "data/preprocessed-data/building_centroids.gpkg"
        ),
        "entrances": Path(pwd, "data/preprocessed-data/entrances.gpkg"),
    },
)

# Preprocess clipped exposure
fiat_preprocess_clip_exp = ScriptMethod(
    script=Path(pwd, "scripts", "preprocess_exposure.py"),
    input={
        "census": fiat_clip_exp.output.census,
        "building_footprints": fiat_clip_exp.output.building_footprints,
        "entrances": fiat_clip_exp.output.entrances,
    },
    output={
        "preprocessed_data_catalog": Path(
            pwd, "data/preprocessed-data/data_catalog.yml"
        ),
    },
)
# %%
# Fiat build
# Before running the FIAT build make sure that the hydromt_fiat config contains
# proper names based on the ones specified in produced/preprocessed data catalog

fiat_build = FIATBuild(
    region=sfincs_build.output.sfincs_region,
    ground_elevation=sfincs_build.output.sfincs_subgrid_dep,
    fiat_root="models/fiat",
    data_libs=data_libs.append(
        fiat_preprocess_clip_exp.output.preprocessed_data_catalog
    ),
    config=w.get_ref("$config.hydromt_fiat_config"),
    continent=w.get_ref("$config.continent"),
)
w.add_rule(fiat_build, rule_id="fiat_build")

# %%
# Preprocess local precipitation data and get design events for both future and current climate conditions
# Preprocess precipitation
precipitation = ScriptMethod(
    script=Path(pwd, "scripts", "preprocess_local_precip.py"),
    output={
        "precip_nc": Path(
            pwd, "data/preprocessed-data/output_scalar_resampled_precip_station11.nc"
        )
    },
)

# Derive desing pluvial events for the current conditions based on the preprocessed local precipitation
pluvial_events_current = PluvialDesignEvents(
    precip_nc=precipitation.output.precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_events_current",
    event_root="events",
)
w.add_rule(pluvial_events_current, rule_id="pluvial_events")

# Derive desing pluvial events for future climate conditions by scaling the current design events
pluvial_events_future = FutureClimateRainfall(
    dT="{future_climate_dT}",
    event_root="events",
    event_set_yaml=pluvial_events_current.output.event_set_yaml,
    wildcard="pluvial_events_future",
)

# Combine current and future design events into one set
all_events = w.wildcards.get("pluvial_events_current") + w.wildcards.get(
    "pluvial_events_future"
)
w.wildcards.set("all_events", all_events)

# %%
# Update the sfincs model with pluvial events
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml="events/{all_events}.yml",
)
w.add_rule(sfincs_update, rule_id="sfincs_update")

# %%
# Run the sfincs model
sfincs_run = SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

# %%
# Downscale Sfincs output to inundation maps.
sfincs_down = SfincsDownscale(
    sfincs_map=sfincs_run.output.sfincs_map,
    sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
    depth_min=w.get_ref("$config.depth_min"),
    output_root="output",
    event_name="{all_events}",
)

# %%
# Postprocesses SFINCS results
sfincs_post = SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
    event_name="{all_events}",
)
w.add_rule(sfincs_post, rule_id="sfincs_post")

# %%
# Update and run FIAT for both event sets
# Set the combined event_set of both fluvial and pluvial
w.wildcards.set("event_set", ["pluvial_events_current", "pluvial_events_future"])

# Update hazard
fiat_update = FIATUpdateHazard(
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml="events/{event_set}.yml",
    map_type="water_level",
    hazard_maps=sfincs_post.output.sfincs_zsmax,
    risk=w.get_ref("$config.risk"),
)
w.add_rule(fiat_update, rule_id="fiat_update")

# Run FIAT
fiat_run = FIATRun(
    fiat_cfg=fiat_update.output.fiat_out_cfg,
    fiat_bin=w.get_ref("$config.fiat_exe"),
)
w.add_rule(fiat_run, rule_id="fiat_run")

# %%
# run workflow
w.dryrun()

# %%
# to snakemake
w.to_snakemake()
