"""Script to generate workflow files for the Rio case using global data."""

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
from hydroflows.workflow.workflow_config import WorkflowConfig

# Where the current file is located
pwd = Path(__file__).parent

# %%
# General setup of workflow
# Define variables
name = "global"
setup_root = Path(pwd, "setups", name)
# Create the case directory
setup_root.mkdir(exist_ok=True, parents=True)
os.chdir(setup_root)
# Setup the log file
setuplog(path=setup_root / "hydroflows.log", level="DEBUG")

# %%
# Setup the config file
config = WorkflowConfig(
    # general settings
    region=Path(pwd, "data/region.geojson"),
    data_libs=[Path(pwd, "data/global-data/data_catalog.yml")],
    plot_fig=True,
    start_date="1990-01-01",
    end_date="2023-12-31",
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
)

# %%
# Setup the workflow
w = Workflow(config=config, name=name, root=setup_root)

# %%
# Sfincs build
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

# %%
# Fiat build
fiat_build = FIATBuild(
    region=sfincs_build.output.sfincs_region,
    ground_elevation=sfincs_build.output.sfincs_subgrid_dep,
    fiat_root="models/fiat",
    data_libs=w.get_ref("$config.data_libs"),
    config=w.get_ref("$config.hydromt_fiat_config"),
    continent=w.get_ref("$config.continent"),
)
w.add_rule(fiat_build, rule_id="fiat_build")

# %%
# Pluvial events (get data + derive events)
# Get ERA5 data
pluvial_data = GetERA5Rainfall(
    region=sfincs_build.output.sfincs_region,
    data_root=Path(pwd, "data/global-data"),
    start_date=w.get_ref("$config.start_date"),
    end_date=w.get_ref("$config.end_date"),
)
w.add_rule(pluvial_data, rule_id="pluvial_data")

# Derive desing pluvial events based on the downloaded (ERA5) data
pluvial_events = PluvialDesignEvents(
    precip_nc=pluvial_data.output.precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_events",
    event_root="events",
)
w.add_rule(pluvial_events, rule_id="pluvial_events")

# %%
# Update the sfincs model with pluvial events
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=pluvial_events.output.event_yaml,
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
# Postprocesses SFINCS results
sfincs_post = SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
)
w.add_rule(sfincs_post, rule_id="sfincs_post")

# %%
# Update FIAT hazard
fiat_update = FIATUpdateHazard(
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml=pluvial_events.output.event_set_yaml,
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
