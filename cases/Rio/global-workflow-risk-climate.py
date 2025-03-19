"""Script to generate workflow files for the flood risk assessment of the Rio case using global data."""

# %%
# Import packages
import subprocess
from pathlib import Path

from hydroflows import Workflow, WorkflowConfig
from hydroflows.log import setuplog
from hydroflows.methods import fiat, rainfall, sfincs

# Where the current file is located
pwd = Path(__file__).parent

# %%
# General setup of workflow
# Define variables
name = "global"
setup_root = Path(pwd, "setups", name)
# Setup the log file
setuplog(path=setup_root / "hydroflows-logger-risk-climate.log", level="DEBUG")

# %%
# Setup the config file
config = WorkflowConfig(
    # general settings
    region=Path(pwd, "data/region.geojson"),
    catalog_path=Path(pwd, "data/global-data/data_catalog.yml"),
    plot_fig=True,
    # sfincs settings
    hydromt_sfincs_config=Path(setup_root, "hydromt_config/sfincs_config_default.yml"),
    sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
    depth_min=0.05,
    subgrid_output=True,  # sfincs subgrid output should exist since it is used in the fiat model
    # fiat settings
    hydromt_fiat_config=Path(setup_root, "hydromt_config/fiat_config.yml"),
    fiat_exe=Path(pwd, "bin/fiat_v0.2.1/fiat.exe"),
    risk=True,
    # design events settings
    rps=[5, 10, 100],
    start_date="1990-01-01",
    end_date="2023-12-31",
    # Climate rainfall scenarios settings (to be applied on the derived design events)
    # Dictionary where:
    # - Key: Scenario name (e.g., "current", "rcp45", "rcp85")
    # - Value: Corresponding temperature delta (dT) for each scenario
    scenarios_dict={
        "present": 0,  # No temperature change for the present (or historical) scenario
        "rcp45_2050": 1.2,  # Moderate emissions scenario with +1.2°C
        "rcp85_2050": 2.5,  # High emissions scenario with +2.5°C
    },
)

# %%
# Setup the workflow
w = Workflow(config=config, name=name, root=setup_root)

# %%
# Sfincs build
sfincs_build = sfincs.SfincsBuild(
    region=w.get_ref("$config.region"),
    sfincs_root="models/sfincs_default",
    config=w.get_ref("$config.hydromt_sfincs_config"),
    catalog_path=w.get_ref("$config.catalog_path"),
    plot_fig=w.get_ref("$config.plot_fig"),
    subgrid_output=w.get_ref("$config.subgrid_output"),
)
w.create_rule(sfincs_build, rule_id="sfincs_build")

# %%
# Fiat build
fiat_build = fiat.FIATBuild(
    region=sfincs_build.output.sfincs_region,
    ground_elevation=sfincs_build.output.sfincs_subgrid_dep,
    fiat_root="models/fiat_default",
    catalog_path=w.get_ref("$config.catalog_path"),
    config=w.get_ref("$config.hydromt_fiat_config"),
)
w.create_rule(fiat_build, rule_id="fiat_build")

# %%
# Pluvial events (get data + derive events)
# Get ERA5 data
pluvial_data = rainfall.GetERA5Rainfall(
    region=sfincs_build.output.sfincs_region,
    data_root=Path(pwd, "data/global-data"),
    start_date=w.get_ref("$config.start_date"),
    end_date=w.get_ref("$config.end_date"),
)
w.create_rule(pluvial_data, rule_id="get_ERA5_data")

# Derive desing pluvial events based on the downloaded (ERA5) data
pluvial_design_events = rainfall.PluvialDesignEvents(
    precip_nc=pluvial_data.output.precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_design_events",
    event_root="events/design",
)
w.create_rule(pluvial_design_events, rule_id="derive_pluvial_design_events")

# %%
# Climate rainfall scenarios events
scenarios_design_events = rainfall.FutureClimateRainfall(
    scenarios=w.get_ref("$config.scenarios_dict"),
    event_names=pluvial_design_events.params.event_names,
    event_set_yaml=pluvial_design_events.output.event_set_yaml,
    event_wildcard="pluvial_design_events",  # we overwrite the wildcard
    scenario_wildcard="scenarios",
    event_root="events",
)
w.create_rule(scenarios_design_events, rule_id="scenarios_pluvial_design_events")

# %%
# Update the sfincs model with pluvial events
sfincs_update = sfincs.SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=scenarios_design_events.output.future_event_yaml,
    output_dir=sfincs_build.output.sfincs_inp.parent / "simulations_{scenarios}",
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
    output_root="output/hazard_default",
)
w.create_rule(sfincs_down, rule_id="sfincs_downscale")

# %%
# Postprocesses SFINCS results (zsmax variable to the global zsmax on a regular grid for FIAT)
sfincs_post = sfincs.SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
    output_root=sfincs_run.output.sfincs_map.parent,
)
w.create_rule(sfincs_post, rule_id="sfincs_post")

# %%
# Update/run FIAT for the event sets and visualize the results

# Update FIAT hazard
fiat_update = fiat.FIATUpdateHazard(
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml=scenarios_design_events.output.future_event_set_yaml,
    map_type="water_level",
    hazard_maps=sfincs_post.output.sfincs_zsmax,
    risk=w.get_ref("$config.risk"),
    output_dir=fiat_build.output.fiat_cfg.parent / "simulations_{scenarios}",
)
w.create_rule(fiat_update, rule_id="fiat_update")

# Run FIAT
fiat_run = fiat.FIATRun(
    fiat_cfg=fiat_update.output.fiat_out_cfg,
    fiat_exe=w.get_ref("$config.fiat_exe"),
)
w.create_rule(fiat_run, rule_id="fiat_run")

# Visualize FIAT results
fiat_visualize_risk = fiat.FIATVisualize(
    fiat_output_csv=fiat_run.output.fiat_out_csv,
    fiat_cfg=fiat_build.output.fiat_cfg,
    spatial_joins_cfg=fiat_build.output.spatial_joins_cfg,
    output_dir=fiat_run.output.fiat_out_csv.parent,
)
w.create_rule(fiat_visualize_risk, rule_id="fiat_visualize_risk")
# %%
# Setup FloodAdapt with the models above and the design events
# floodadapt_build = flood_adapt.SetupFloodAdapt(
#     sfincs_inp=sfincs_build.output.sfincs_inp,
#     fiat_cfg=fiat_build.output.fiat_cfg,
#     event_set_yaml=pluvial_design_events.output.event_set_yaml,
#     output_dir="models/flood_adapt_builder_default",
# )
# w.create_rule(floodadapt_build, rule_id="floodadapt_build")
# %%
# run workflow
w.dryrun()

# %%
# to snakemake
w.to_snakemake("global-workflow-risk-climate.smk")

# %%
# (test) run the workflow with snakemake and visualize the directed acyclic graph
subprocess.run(
    "snakemake -s global-workflow-risk-climate.smk --configfile global-workflow-risk-climate.config.yml --dag | dot -Tsvg > dag-risk-climate.svg",
    cwd=w.root,
    shell=True,
).check_returncode()
# %%
