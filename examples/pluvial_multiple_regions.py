"""Run pluvial design events with existing SFINCS model."""

# %%
# Import modules
import subprocess
from pathlib import Path

from hydroflows.methods.rainfall import GetERA5Rainfall, PluvialDesignEvents
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsDownscale,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow import Workflow, WorkflowConfig

# Where the file is currently located
pwd = Path(__file__).parent

# %%
# Fetch the build data
cache_dir = fetch_data(data="global-data")

# Setup workflow settings and configuration
name = "pluvial_multiple_regions"
case_root = Path(pwd, "cases", name)

# Setup the configuration
config = WorkflowConfig(
    config=Path(pwd, "hydromt_config/sfincs_config.yml"),
    data_libs=[Path(cache_dir, "data_catalog.yml")],
    sfincs_exe=Path(pwd, "../bin/sfincs_v2.1.1/sfincs.exe"),
    start_date="2014-01-01",
    end_date="2021-12-31",
    # sfincs settings
    hydromt_sfincs_config=Path(pwd, "hydromt_config/sfincs_config.yml"),
    # design event settings
    rps=[2, 5, 10],
)

# %%
# Setup the workflow
w = Workflow(
    config=config,
    wildcards={"region": ["region", "region2"]},
    name=name,
    root=case_root,
)

# %%
# Build the SFINCS models
sfincs_build = SfincsBuild(
    region="../../data/build/{region}.geojson",  # NOTE: case in sub-subfolder of pwd
    sfincs_root="models/sfincs/{region}",
    default_config=w.get_ref("$config.hydromt_sfincs_config"),
    data_libs=w.get_ref("$config.data_libs"),
)
w.add_rule(sfincs_build, "sfincs_build")

# %%
# Get Rainfall timeseries
get_rainfall = GetERA5Rainfall(
    region=sfincs_build.output.sfincs_region,
    data_root="data/era5/{region}",
    start_date=w.get_ref("$config.start_date"),
    end_date=w.get_ref("$config.end_date"),
)
w.add_rule(get_rainfall, rule_id="get_rainfall")

# %%
# Derive pluvial events from rainfall data
pluvial_events = PluvialDesignEvents(
    precip_nc=get_rainfall.output.precip_nc,
    event_root="data/events/{region}",
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_events",
)
w.add_rule(pluvial_events, rule_id="pluvial_events")

# %%
# Update the SFINCS models
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=pluvial_events.output.event_yaml,
    event_name="{pluvial_events}",
)
w.add_rule(sfincs_update, rule_id="sfincs_update")

# %%
# Run SFINCS model
sfincs_run = SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

# Post process the results from pluvial events
sfincs_post = SfincsDownscale(
    sfincs_map=sfincs_run.output.sfincs_map,
    sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
    output_root="output/{region}",
)
w.add_rule(sfincs_post, "sfincs_post")

# %%
# Do a dry run of the workflow
w.dryrun()

# %%
# Write the workflow to a Snakefile
w.to_snakemake()

# %%
# (test) run the workflow with snakemake
# test snakefile
subprocess.run(["snakemake", "-n"], cwd=w.root)
# uncomment to run the workflow
# subprocess.run(["snakemake", "-s"], cwd=w.root)
