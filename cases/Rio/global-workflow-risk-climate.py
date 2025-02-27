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
setuplog(
    path=setup_root / "hydroflows-logger-risk-climate-strategies.log", level="DEBUG"
)

# %%
# Setup the config file
config = WorkflowConfig(
    # general settings
    region=Path(pwd, "data/region.geojson"),
    catalog_path=Path(pwd, "data/global-data/data_catalog.yml"),
    plot_fig=True,
    # sfincs settings
    sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
    depth_min=0.05,
    # fiat settings
    hydromt_fiat_config=Path(setup_root, "hydromt_config/fiat_config.yml"),
    fiat_exe=Path(pwd, "bin/fiat_v0.2.1/fiat.exe"),
    risk=True,
    # design events settings
    rps=[5, 10, 100],
    start_date="1990-01-01",
    end_date="2023-12-31",
)

# Futute climate rainfall design events settings
scenarios = ["rcp45", "rcp85"]
dTs = [1.2, 2.5]

# Wildcard names for current and future conditions events
wildcard_design_events = ("pluvial_design_events",)
wildcard_future_events = "future_pluvial_design_events"

# Strategies settings
strategies = ["default", "reservoirs"]
strategies_dict = {"strategies": strategies}
# %%
# Setup the workflow
w = Workflow(config=config, name=name, root=setup_root, wildcards=strategies_dict)

# %%
# Sfincs build
sfincs_build = sfincs.SfincsBuild(
    region=w.get_ref("$config.region"),
    sfincs_root="models/sfincs_{strategies}",
    config=Path(setup_root, "hydromt_config/sfincs_config_{strategies}.yml"),
    catalog_path=w.get_ref("$config.catalog_path"),
    plot_fig=w.get_ref("$config.plot_fig"),
)
w.add_rule(sfincs_build, rule_id="sfincs_build")

# %%
# Fiat build
fiat_build = fiat.FIATBuild(
    region=sfincs_build.output.sfincs_region,
    ground_elevation=sfincs_build.output.sfincs_subgrid_dep,
    fiat_root="models/fiat",
    catalog_path=w.get_ref("$config.catalog_path"),
    config=w.get_ref("$config.hydromt_fiat_config"),
)
w.add_rule(fiat_build, rule_id="fiat_build")

# %%
# Pluvial events (get data + derive events)
# Get ERA5 data
pluvial_data = rainfall.GetERA5Rainfall(
    region=sfincs_build.output.sfincs_region,
    data_root=Path(pwd, "data/global-data"),
    start_date=w.get_ref("$config.start_date"),
    end_date=w.get_ref("$config.end_date"),
)
w.add_rule(pluvial_data, rule_id="pluvial_data")

# Derive desing pluvial events based on the downloaded (ERA5) data
pluvial_events = rainfall.PluvialDesignEvents(
    precip_nc=pluvial_data.output.precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard=wildcard_design_events,
    event_root="events",
)
w.add_rule(pluvial_events, rule_id=wildcard_design_events)

# %%
# Futute climate rainfall design events

# loop over scenarios and dTs
for scenario, dT in zip(scenarios, dTs):
    future_design_events = rainfall.FutureClimateRainfall(
        scenario_name=scenario,
        event_names_input=["p_event01", "p_event02", "p_event03"],
        event_set_yaml=pluvial_events.output.event_set_yaml,
        dT=dT,
        wildcard=f"{wildcard_future_events}_{scenario}",
        event_root="events",
    )
    w.add_rule(future_design_events, rule_id=f"{wildcard_future_events}_{scenario}")

# %%
# Merge the pluvial events with the future events
scenarios_wildcards = [f"{wildcard_future_events}_{scenario}" for scenario in scenarios]
scenarios_events = []
for scenario_wildcard in scenarios_wildcards:
    scenarios_events += w.wildcards.get(scenario_wildcard)

all_events = w.wildcards.get(wildcard_design_events) + scenarios_events
w.wildcards.set("all_events", all_events)

# %%
# Update the sfincs model with pluvial events
sfincs_update = sfincs.SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml="events/{all_events}.yml",
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
# Postprocesses SFINCS results (zsmax variable to the global zsmax on a regular grid for FIAT)
sfincs_post = sfincs.SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
)
w.add_rule(sfincs_post, rule_id="sfincs_post")

# %%
# run workflow
w.dryrun()

# %%
# to snakemake
w.to_snakemake("global-workflow-risk-climate.smk")

# %%
# (test) run the workflow with snakemake and visualize the directed acyclic graph
subprocess.run(
    "snakemake -s global-workflow-risk-climate.smk --configfile global-workflow-risk-climate.config.yml --dag | dot -Tsvg > dag-risk.svg",
    cwd=w.root,
    shell=True,
).check_returncode()
# %%
