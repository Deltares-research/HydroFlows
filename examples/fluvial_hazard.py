"""Build pluvial & fluvial flood risk workflow."""

# %% Import packages
from hydroflows import Workflow
from hydroflows.methods.discharge import FluvialDesignEvents
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsPostprocess,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.methods.wflow import (
    WflowBuild,
    WflowRun,
    WflowUpdateForcing,
)
from hydroflows.workflow.workflow_config import WorkflowConfig

# %% Create a workflow  with initial config
conf = WorkflowConfig(
    sfincs_exe="bin/sfincs/sfincs.exe",
    wflow_bin="bin/wflow/wflow_cli.exe",
    rps=[2, 100],
)

w = Workflow(name="fluvial_hazard", config=conf)

# %% build SFINCS model
sfincs_build = SfincsBuild(region="data/region.geojson", sfincs_root="models/sfincs")
w.add_rule(sfincs_build, rule_id="sfincs_build")

# %% build WFLOW model
wflow_build = WflowBuild(
    region=sfincs_build.output.sfincs_region, wflow_root="models/wflow"
)
w.add_rule(wflow_build, rule_id="wflow_build")


# %% update forcing & run wflow model
wflow_update = WflowUpdateForcing(
    wflow_toml=wflow_build.output.wflow_toml,
    start_time="1990-01-01",
    end_time="2023-12-31",
    sim_subfolder="reanalysis",
)
w.add_rule(wflow_update, rule_id="wflow_update")

wflow_run = WflowRun(
    wflow_toml=wflow_update.output.wflow_out_toml,
    wflow_bin=w.get_ref("$config.wflow_bin"),
)
w.add_rule(wflow_run, rule_id="wflow_run")

# %% derive fluvial design events
fluvial_events = FluvialDesignEvents(
    discharge_nc=wflow_run.output.wflow_output_timeseries,
    rps=w.get_ref("$config.rps"),
    wildcard="event",
    event_root="data/events",
)
w.add_rule(fluvial_events, rule_id="fluvial_events")


# %% prepare sfincs models per event, run & postprocess
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=fluvial_events.output.event_yaml,
)
w.add_rule(sfincs_update, rule_id="sfincs_update")

sfincs_run = SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

sfincs_post = SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
    sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
)
w.add_rule(sfincs_post, rule_id="sfincs_post")

# %% print workflow
print(w)

# %% Test the workflow
w.run(dryrun=True, tmpdir="./")

# %% Write the workflow to a Snakefile
w.to_snakemake(f"{w.name}.smk")

# %%
