from hydroflows import Workflow
from hydroflows.methods import (
    GetERA5Rainfall,
    PluvialDesignEvents,
    SfincsBuild,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.workflow.workflow_config import WorkflowConfig

# set up the config section
config = WorkflowConfig(
    sfincs_exe="bin/sfincs/sfincs.exe",
    rps=[2, 50, 100],
)

# Create an empty workflow
workflow = Workflow(config=config)

# create a bunch of rules
sfincs_build = SfincsBuild(
    region=r"data/test_region.geojson",
)


get_ERA5_rainfall = GetERA5Rainfall(
    # region=sfincs_build.output.sfincs_region, # no ref
    # region=w.get_ref("$rules.sfincs_build.output.sfincs_region"), # ref option 1
    region=workflow.get_ref("sfincs_build.output.sfincs_region")  # ref option 2
)


pluvial_events = PluvialDesignEvents(
    precip_nc=get_ERA5_rainfall.output.precip_nc,
    rps=workflow.get_ref("$config.rps"),
    wildcard="pluvial_event",
)

# %%
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=pluvial_events.output.event_yaml,
)

# %%
sfincs_run = SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=workflow.get_ref("$config.sfincs_exe"),
)

# add all rules to workflow consecutively
workflow.add_rule(sfincs_build, rule_id="sfincs_build")
workflow.add_rule(get_ERA5_rainfall, rule_id="get_ERA5_rainfall")
workflow.add_rule(pluvial_events, rule_id="pluvial_events")
workflow.add_rule(sfincs_update, rule_id="sfincs_update")
workflow.add_rule(sfincs_run, rule_id="sfincs_run")
