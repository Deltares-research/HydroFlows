"""Pluvial hazard workflow parsed to CWL."""

"""
Differences vs parsing to snakemake:
- All variables/information that a user provides to configure the workflow must be added to the config.
  The config is used to generate the file listing all inputs to the workflow, and all inputs must be present there.
- Currently, all inputs/outputs passed between rules must be given as reference objects. This will be addressed later.
"""
# %%
from pathlib import Path

from hydroflows.methods.rainfall import GetERA5Rainfall, PluvialDesignEvents
from hydroflows.methods.sfincs import SfincsBuild,SfincsRun, SfincsUpdateForcing
from hydroflows.workflow import Workflow, WorkflowConfig

# %%
config = WorkflowConfig(
    sfincs_root = Path("./testfolder/models/sfincs"),
    region = Path("./testfolder/data/region.geojson"),
    wildcard_name = "event",
    sfincs_vm='docker',
    sfincs_tag='latest',
    rps=[2, 5, 10])

# %%
w = Workflow(name="pluvial_cwl", config=config)

# %%
sfincs_build = SfincsBuild(
    sfincs_root=w.get_ref("$config.sfincs_root"),
    region=w.get_ref("$config.region")
)

w.add_rule(sfincs_build, rule_id="sfincs_build")

# %%
era5_rainfall = GetERA5Rainfall(
    region=w.get_ref("$rules.sfincs_build.output.sfincs_region"),
)
w.add_rule(era5_rainfall, rule_id="get_ERA5")

pluvial_events = PluvialDesignEvents(
    precip_nc=w.get_ref("$rules.get_ERA5.output.precip_nc"),
    rps=w.get_ref("$config.rps"),
    wildcard=w.get_ref("$config.wildcard_name")
)
w.add_rule(pluvial_events, rule_id="pluvial_events")

# %%
sfincs_pre = SfincsUpdateForcing(
    sfincs_inp=w.get_ref("$rules.sfincs_build.output.sfincs_inp"),
    event_yaml=w.get_ref("$rules.pluvial_events.output.event_yaml")
)
w.add_rule(sfincs_pre, rule_id="sfincs_pre")

sfincs_run = SfincsRun(
    sfincs_inp=w.get_ref("$rules.sfincs_pre.output.sfincs_out_inp"),
    vm=w.get_ref("$config.sfincs_vm"),
    docker_tag=w.get_ref("$config.sfincs_tag")
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

# %%

w.to_cwl(
    cwlfile=f"{w.name}.cwl",
    dryrun=True
)