"""Build pluvial & fluvial flood risk workflow."""

# %% Import packages
from hydroflows import Workflow
from hydroflows.methods.fiat import FIATBuild, FIATRun, FIATUpdateHazard
from hydroflows.methods.rainfall import (
    GetERA5Rainfall,
    PluvialDesignEvents,
)
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsPostprocess,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.methods.wflow import (
    WflowBuild,
    WflowDesignHydro,
    WflowRun,
    WflowUpdateForcing,
)
from hydroflows.workflow.workflow_config import WorkflowConfig

# %% Create a workflow  with initial config
conf = WorkflowConfig(
    sfincs_exe="bin/sfincs/sfincs.exe",
    wflow_bin="bin/wflow/wflow_cli.exe",
    fiat_bin="bin/fiat/fiat.exe",
    rps=[2, 100],
)

w = Workflow(name="pluvial_fluvial_risk", config=conf)

# %% build SFINCS model
sfincs_build = SfincsBuild(
    region="data/test_region.geojson", sfincs_root="models/sfincs"
)
w.add_rule(sfincs_build, rule_id="sfincs_build")

# %% build FIAT model
build_fiat = FIATBuild(
    region=sfincs_build.output.sfincs_region, fiat_root="models/fiat"
)
w.add_rule(build_fiat, rule_id="build_fiat")

# %% build WFLOW model
wflow_build = WflowBuild(
    region=sfincs_build.output.sfincs_region, wflow_root="models/wflow"
)
w.add_rule(wflow_build, rule_id="wflow_build")

# %% get rainfall data for domain
get_precip = GetERA5Rainfall(region=sfincs_build.output.sfincs_region)
w.add_rule(get_precip, rule_id="get_precip")

# %% derive pluvial design events
pluvial_events = PluvialDesignEvents(
    precip_nc=get_precip.output.precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_event",
    event_root="data/events",
)
w.add_rule(pluvial_events, rule_id="pluvial_events")

# %% update forcing for wflow model
wflow_update = WflowUpdateForcing(
    wflow_toml=wflow_build.output.wflow_toml,
    start_time="1990-01-01",
    end_time="2023-12-31",
    sim_subfolder="reanalysis",
)
w.add_rule(wflow_update, rule_id="wflow_update")

# %% run wflow model
wflow_run = WflowRun(
    wflow_toml=wflow_update.output.wflow_out_toml,
    wflow_bin=w.get_ref("$config.wflow_bin"),
)
w.add_rule(wflow_run, rule_id="wflow_run")

# %% derive fluvial design events
fluvial_events = WflowDesignHydro(
    discharge_nc=wflow_run.output.wflow_output_timeseries,
    rps=w.get_ref("$config.rps"),
    wildcard="fluvial_event",
    event_root="data/events",
)
w.add_rule(fluvial_events, rule_id="fluvial_events")

# %% create new wildcard for all events (pluvial and fluvial)
all_events = w.wildcards.get("pluvial_event") + w.wildcards.get("fluvial_event")
w.wildcards.set("all_events", all_events)

# %% prepare sfincs models per event
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml="data/events/{all_events}.yml",
)
w.add_rule(sfincs_update, rule_id="sfincs_update")

# %% add sfics run and postprocess rules
sfincs_run = SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

sfincs_post = SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
    sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
    event_name="{all_events}",
)
w.add_rule(sfincs_post, rule_id="sfincs_post")

# %% create wildcard per event set add fiat update rule
w.wildcards.set("event_set", ["pluvial_events", "fluvial_events"])

fiat_update = FIATUpdateHazard(
    fiat_cfg=build_fiat.output.fiat_cfg,
    event_set_yaml="data/events/{event_set}.yml",
    event_set_name="{event_set}",
    hazard_maps=sfincs_post.output.hazard_tif,
)
w.add_rule(fiat_update, rule_id="fiat_update")
# %%

fiat_run = FIATRun(
    fiat_cfg=fiat_update.output.fiat_out_cfg,
    fiat_bin=w.get_ref("$config.fiat_bin"),
)
w.add_rule(fiat_run, rule_id="fiat_run")

# %% print the workflow
print(w)

# %% Test the workflow
w.run(dryrun=True)

# %% Write the workflow to a Snakefile
w.to_snakemake(f"{w.name}.smk")
