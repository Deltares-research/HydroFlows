"""Build pluvial & fluvial flood risk workflow."""

# %% Import packages
import subprocess
from pathlib import Path

from hydroflows import Workflow
from hydroflows.methods.discharge import FluvialDesignEvents
from hydroflows.methods.fiat import (
    FIATBuild,
    FIATRun,
    FIATUpdateHazard,
)
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
    WflowRun,
    WflowUpdateForcing,
)
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow.workflow_config import WorkflowConfig

# Where the current file is located
pwd = Path(__file__).parent

# %% Fetch the global build data
cache_dir = fetch_data(data="global-data")

# %% General configuration of workflow
name = "pluvial_fluvial_risk"  # for now
case_root = Path(pwd, "cases", name)

config = WorkflowConfig(
    # general settings
    region=Path(pwd, "data/build/region.geojson"),
    data_libs=[Path(cache_dir, "data_catalog.yml")],
    plot_fig=True,
    start_date="2014-01-01",
    end_date="2021-12-31",
    # sfincs settings
    hydromt_sfincs_config=Path(pwd, "hydromt_config/sfincs_config.yml"),
    sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
    sfincs_res=50,
    river_upa=10,
    depth_min=0.05,
    # wflow settings
    hydromt_wflow_config=Path(pwd, "hydromt_config/wflow_config.yml"),
    wflow_exe=Path(pwd, "bin/wflow_v0.8.1/bin/wflow_cli.exe"),
    wflow_res=0.0041667,
    # fiat settings
    hydromt_fiat_config=Path(pwd, "hydromt_config/fiat_config.yml"),
    fiat_exe=Path(pwd, "bin/fiat/fiat.exe"),
    continent="Europe",
    risk=True,
    # design events settings
    rps=[5, 10, 25],
)

# %% Create a workflow
w = Workflow(config=config, name=name, root=case_root)

# %% Sfincs build
sfincs_build = SfincsBuild(
    region=w.get_ref("$config.region"),
    sfincs_root="models/sfincs",
    default_config=w.get_ref("$config.hydromt_sfincs_config"),
    data_libs=w.get_ref("$config.data_libs"),
    res=w.get_ref("$config.sfincs_res"),
    river_upa=w.get_ref("$config.river_upa"),
    plot_fig=w.get_ref("$config.plot_fig"),
)
w.add_rule(sfincs_build, rule_id="sfincs_build")

# %% Wflow build
wflow_build = WflowBuild(
    region=sfincs_build.output.sfincs_region,
    wflow_root="models/wflow",
    default_config=w.get_ref("$config.hydromt_wflow_config"),
    data_libs=w.get_ref("$config.data_libs"),
    gauges=Path(sfincs_build.params.sfincs_root, "gis", "src.geojson"),
    plot_fig=w.get_ref("$config.plot_fig"),
)
w.add_rule(wflow_build, rule_id="wflow_build")

# %% Fiat build
fiat_build = FIATBuild(
    region=sfincs_build.output.sfincs_region,
    ground_elevation=sfincs_build.output.sfincs_subgrid_dep,
    fiat_root="models/fiat",
    data_libs=w.get_ref("$config.data_libs"),
    config=w.get_ref("$config.hydromt_fiat_config"),
    continent=w.get_ref("$config.continent"),
)
w.add_rule(fiat_build, rule_id="fiat_build")

# %% Update and run wflow + generate fluvial events
# Update forcing
wflow_update = WflowUpdateForcing(
    wflow_toml=wflow_build.output.wflow_toml,
    data_libs=w.get_ref("$config.data_libs"),
    start_time=w.get_ref("$config.start_date"),
    end_time=w.get_ref("$config.end_date"),
)
w.add_rule(wflow_update, rule_id="wflow_update")

# Run wflow
wflow_run = WflowRun(
    wflow_toml=wflow_update.output.wflow_out_toml,
    wflow_bin=w.get_ref("$config.wflow_exe"),
)
w.add_rule(wflow_run, rule_id="wflow_run")

# Generate fluvial events
fluvial_events = FluvialDesignEvents(
    discharge_nc=wflow_run.output.wflow_output_timeseries,
    rps=w.get_ref("$config.rps"),
    wildcard="fluvial_events",
    event_root="data/events",
    index_dim="Q_gauges_bounds",
)
w.add_rule(fluvial_events, rule_id="fluvial_events")

# %% Pluvial events
# Get the data

pluvial_data = GetERA5Rainfall(
    region=sfincs_build.output.sfincs_region,
    data_root="data/era5",
    start_date=w.get_ref("$config.start_date"),
    end_date=w.get_ref("$config.end_date"),
)
w.add_rule(pluvial_data, rule_id="pluvial_data")
precip_nc = pluvial_data.output.precip_nc

# Actual derivation of events based on precip
pluvial_events = PluvialDesignEvents(
    precip_nc=precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_events",
    event_root="data/events",
)
w.add_rule(pluvial_events, rule_id="pluvial_events")

# %% Combine fluvial and pluvial events into one set
all_events = w.wildcards.get("pluvial_events") + w.wildcards.get("fluvial_events")
w.wildcards.set("all_events", all_events)

# %% Updating, running and postprocessing SFINCS model for combined events
# Sfincs update with precip
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml="data/events/{all_events}.yml",
)
w.add_rule(sfincs_update, rule_id="sfincs_update")

# Run SFINCS model
sfincs_run = SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

# Postprocesses SFINCS results
sfincs_post = SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
    event_name="{all_events}",
)
w.add_rule(sfincs_post, rule_id="sfincs_post")

# %% Update and run FIAT for both event sets
# Set the combined event_set of both fluvial and pluvial
w.wildcards.set("event_set", ["fluvial_events", "pluvial_events"])

# Update hazard
fiat_update = FIATUpdateHazard(
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml="data/events/{event_set}.yml",
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

# %% Test the workflow
w.dryrun()

# %% Write the workflow to a Snakefile
w.to_snakemake()

# %% (test) run the workflow with snakemake
# dryrun the workflow
subprocess.run(["snakemake", "-n"], cwd=w.root)
# uncomment to run the workflow
# subprocess.run(["snakemake", "-c", "1"], cwd=w.root)
