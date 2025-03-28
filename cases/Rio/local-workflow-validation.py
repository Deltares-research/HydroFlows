"""Script to generate workflow files for the Rio case model validation integrating local data."""

# %%
# Import packages
import subprocess
from pathlib import Path

from hydroflows import Workflow, WorkflowConfig
from hydroflows.log import setuplog
from hydroflows.methods import (
    catalog,
    hazard_validation,
    historical_events,
    script,
    sfincs,
)

# Where the current file is located
pwd = Path(__file__).parent

# %%
# General setup of workflow
# Define variables
name = "local"
setup_root = Path(pwd, "setups", name)
# Setup the log file
setuplog(path=setup_root / "hydroflows-logger-validation.log", level="DEBUG")

# %%
# Setup the config file
# Config
config = WorkflowConfig(
    # general settings
    region=Path(pwd, "data/region.geojson"),
    catalog_path_global=Path(pwd, "data/global-data/data_catalog.yml"),
    catalog_path_local=Path(pwd, "data/local-data/data_catalog.yml"),
    plot_fig=True,
    # sfincs settings
    hydromt_sfincs_config=Path(setup_root, "hydromt_config/sfincs_config_default.yml"),
    sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
    depth_min=0.05,
    subgrid_output=True,  # sfincs subgrid output should exist since it is used in the fiat model
    # historical events settings
    historical_events_dates={
        "event_january_2024": {
            "startdate": "2024-01-12 23:00",
            "enddate": "2024-01-14 21:00",
        },
    },
    # validation settings
    floodmarks_geom=Path(pwd, "data/local-data/floodmap/laminas_levantadas.gpkg"),
    waterlevel_col="altura_cm",
    waterlevel_unit="cm",
    cmap="PiYG",
    bins=[-2.5, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5],
    bmap="CartoDB.PositronNoLabels",
)

# %%
# Setup the workflow
w = Workflow(
    config=config,
    name=name,
    root=setup_root,
)

# %%
# Merge global and local data catalogs
merged_catalog_global_local = catalog.MergeCatalogs(
    catalog_path1=w.get_ref("$config.catalog_path_global"),
    catalog_path2=w.get_ref("$config.catalog_path_local"),
    merged_catalog_path=Path(pwd, "data/merged_data_catalog_local_global.yml"),
)
w.create_rule(merged_catalog_global_local, rule_id="merge_global_local_catalogs")

# %%
# Sfincs build
sfincs_build = sfincs.SfincsBuild(
    region=w.get_ref("$config.region"),
    sfincs_root="models/sfincs_default",
    config=w.get_ref("$config.hydromt_sfincs_config"),
    catalog_path=merged_catalog_global_local.output.merged_catalog_path,
    plot_fig=w.get_ref("$config.plot_fig"),
    subgrid_output=w.get_ref("$config.subgrid_output"),
)
w.create_rule(sfincs_build, rule_id="sfincs_build")

# %%
# Preprocess local precipitation data and get the historical event for validation, i.e January's 2024
# Preprocess precipitation
precipitation = script.ScriptMethod(
    script=Path(pwd, "scripts", "preprocess_local_precip.py"),
    output={
        "precip_nc": Path(
            pwd, "data/preprocessed-data/output_scalar_resampled_precip_station11.nc"
        )
    },
)
w.create_rule(precipitation, rule_id="preprocess_local_rainfall")

historical_event = historical_events.HistoricalEvents(
    precip_nc=precipitation.output.precip_nc,
    events_dates=w.get_ref("$config.historical_events_dates"),
    output_dir="events/historical",
    wildcard="pluvial_historical_event",
)
w.create_rule(historical_event, rule_id="historical_event")

# %%
# Update the sfincs model with pluvial events
sfincs_update = sfincs.SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=historical_event.output.event_yaml,
)
w.create_rule(sfincs_update, rule_id="sfincs_update")

# %%
# Run the sfincs model
sfincs_run = sfincs.SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.create_rule(sfincs_run, rule_id="sfincs_run")

# %%
# Downscale Sfincs output to inundation maps.
sfincs_down = sfincs.SfincsDownscale(
    sfincs_map=sfincs_run.output.sfincs_map,
    sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
    depth_min=w.get_ref("$config.depth_min"),
    output_root="output/hazard_historical",
)
w.create_rule(sfincs_down, rule_id="sfincs_downscale")

# %%
# Validate the downscaled inundation map against floodmarks
floodmark_validation = hazard_validation.FloodmarksValidation(
    floodmarks_geom=w.get_ref("$config.floodmarks_geom"),
    flood_hazard_map=sfincs_down.output.hazard_tif,
    waterlevel_col=w.get_ref("$config.waterlevel_col"),
    waterlevel_unit=w.get_ref("$config.waterlevel_unit"),
    out_root="output/validation/{pluvial_historical_event}",
    bmap=w.get_ref("$config.bmap"),
    bins=w.get_ref("$config.bins"),
    cmap=w.get_ref("$config.cmap"),
    region=sfincs_build.output.sfincs_region,
)
w.create_rule(floodmark_validation, rule_id="floodmark_validation")

# %%
# run workflow
w.dryrun()

# %%
# to snakemake
w.to_snakemake("local-workflow-validation.smk")

# %%
# (test) run the workflow with snakemake and visualize the directed acyclic graph
subprocess.run(
    "snakemake -s local-workflow-validation.smk --configfile local-workflow-validation.config.yml --dag | dot -Tsvg > dag-validation.svg",
    cwd=w.root,
    shell=True,
).check_returncode()

# %%
