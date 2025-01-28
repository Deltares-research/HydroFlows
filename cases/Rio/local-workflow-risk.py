"""Script to generate workflow files for the Rio case flood risk assessment using local data."""

# %%
# Import packages
import os
import subprocess
from pathlib import Path

from hydroflows import Workflow, WorkflowConfig
from hydroflows.log import setuplog
from hydroflows.methods import fiat, flood_adapt, rainfall, script, sfincs

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
setuplog(path=setup_root / "hydroflows-logger-risk.log", level="DEBUG")

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
    depth_min=0.05,
    # fiat settings
    hydromt_fiat_config=Path(setup_root, "hydromt_config/fiat_config.yml"),
    fiat_exe=Path(pwd, "bin/fiat_v0.2.0/fiat.exe"),
    risk=True,
    # design events settings
    rps=[5, 10, 25],
    start_date="1990-01-01",
    end_date="2023-12-31",
)

# Data libs (outside config as we will append the preprocessed dc)
data_libs = [
    Path(pwd, "data/local-data/data_catalog.yml"),
    Path(pwd, "data/global-data/data_catalog.yml"),
]

# %%
# Setup the workflow
w = Workflow(
    config=config,
    name=name,
    root=setup_root,
)

# %%
# Sfincs build
sfincs_build = sfincs.SfincsBuild(
    region=w.get_ref("$config.region"),
    sfincs_root="models/sfincs",
    config=w.get_ref("$config.hydromt_sfincs_config"),
    data_libs=data_libs,
    plot_fig=w.get_ref("$config.plot_fig"),
)
w.add_rule(sfincs_build, rule_id="sfincs_build")

# %%
# Preprocess local FIAT data scripts (clip exposure & preprocess clipped exposure)

# Clip exposure datasets to the region of interest.
fiat_clip_exp = script.ScriptMethod(
    script=Path(pwd, "scripts", "clip_exposure.py"),
    # Note that the output paths/names are hardcoded in the scipt
    # the same applies to the data catalog
    input={
        "region": sfincs_build.output.sfincs_region,
    },
    output={
        "census": Path(pwd, "data/preprocessed-data/census20102.gpkg"),
        "building_footprints": Path(
            pwd, "data/preprocessed-data/building_footprints.gpkg"
        ),
        "entrances": Path(pwd, "data/preprocessed-data/entrances.gpkg"),
    },
)
w.add_rule(fiat_clip_exp, rule_id="fiat_clip_exposure")

# Preprocess clipped exposure
fiat_preprocess_clip_exp = script.ScriptMethod(
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
w.add_rule(fiat_preprocess_clip_exp, rule_id="fiat_preprocess_exposure")

# %%
# Fiat build
# Before running the FIAT build make sure that the hydromt_fiat config contains
# proper names based on the ones specified in produced/preprocessed data catalog
data_libs.append(fiat_preprocess_clip_exp.output.preprocessed_data_catalog)
data_libs_with_fiat_local = data_libs

fiat_build = fiat.FIATBuild(
    region=sfincs_build.output.sfincs_region,
    ground_elevation=sfincs_build.output.sfincs_subgrid_dep,
    fiat_root="models/fiat",
    data_libs=data_libs_with_fiat_local,
    config=w.get_ref("$config.hydromt_fiat_config"),
)
w.add_rule(fiat_build, rule_id="fiat_build")

# %%
# Preprocess local precipitation data and get design events for both future and current climate conditions
# Preprocess precipitation
precipitation = script.ScriptMethod(
    script=Path(pwd, "scripts", "preprocess_local_precip.py"),
    output={
        "precip_nc": Path(
            pwd, "data/preprocessed-data/output_scalar_resampled_precip_station11.nc"
        )
    },
)
w.add_rule(precipitation, rule_id="preprocess_local_rainfall")

# Derive desing pluvial events for the current conditions based on the preprocessed local precipitation
pluvial_events = rainfall.PluvialDesignEvents(
    precip_nc=precipitation.output.precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_design_events",
    event_root="events/design",
)
w.add_rule(pluvial_events, rule_id="pluvial_design_events")

# %%
# Update the sfincs model with pluvial events
sfincs_update = sfincs.SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=pluvial_events.output.event_yaml,
)
w.add_rule(sfincs_update, rule_id="sfincs_update")

# %%
# Run the sfincs model
sfincs_run = sfincs.SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

# %%
# Downscale Sfincs output to inundation maps.
sfincs_down = sfincs.SfincsDownscale(
    sfincs_map=sfincs_run.output.sfincs_map,
    sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
    depth_min=w.get_ref("$config.depth_min"),
    output_root="output/hazard",
)
w.add_rule(sfincs_down, rule_id="sfincs_downscale")

# %%
# Postprocesses SFINCS results
sfincs_post = sfincs.SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
)
w.add_rule(sfincs_post, rule_id="sfincs_post")

# %%
# Update and run FIAT for the event set

# Update hazard
fiat_update = fiat.FIATUpdateHazard(
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml=pluvial_events.output.event_set_yaml,
    map_type="water_level",
    hazard_maps=sfincs_post.output.sfincs_zsmax,
    risk=w.get_ref("$config.risk"),
)
w.add_rule(fiat_update, rule_id="fiat_update")

# Run FIAT
fiat_run = fiat.FIATRun(
    fiat_cfg=fiat_update.output.fiat_out_cfg,
    fiat_exe=w.get_ref("$config.fiat_exe"),
)
w.add_rule(fiat_run, rule_id="fiat_run")

# %%
# Setup FloodAdapt
floodadapt_build = flood_adapt.SetupFloodAdapt(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml=pluvial_events.output.event_set_yaml,
    output_dir="models/flood_adapt_builder",
)
w.add_rule(floodadapt_build, rule_id="floodadapt_build")

# %%
# run workflow
w.dryrun()

# %%
# to snakemake
w.to_snakemake("local-workflow-risk.smk")

# %%
# %%
# (test) run the workflow with snakemake and visualize the directed acyclic graph
subprocess.run(
    "snakemake -s local-workflow-risk.smk --configfile local-workflow-risk.config.yml --dag | dot -Tsvg > dag-risk.svg",
    cwd=w.root,
    shell=True,
).check_returncode()
# %%
