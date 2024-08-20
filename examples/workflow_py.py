"""Example of the Workflow class for building workflows in python."""
# %% Import packages
import os

from hydroflows import Workflow
from hydroflows.methods import (
    GetERA5Rainfall,
    PluvialDesignEvents,
    SfincsBuild,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.workflow.workflow_config import WorkflowConfig

# %% Create a workflow config

conf = WorkflowConfig(
    sfincs_exe="bin/sfincs/sfincs.exe",
    rps=[2, 50, 100],
)

# %% Create a workflow
w = Workflow(config=conf)

sfincs_build = SfincsBuild(
    region=r"data/test_region.geojson",
)
w.add_rule(sfincs_build, rule_id="sfincs_build")
# %%
get_precip = GetERA5Rainfall(
    # region=sfincs_build.output.sfincs_region, # no ref
    # region=w.get_ref("$rules.sfincs_build.output.sfincs_region"), # ref option 1
    region=w.get_ref("sfincs_build.output.sfincs_region")  # ref option 2
)
w.add_rule(get_precip, rule_id="get_precip")

# %%
pluvial_events = PluvialDesignEvents(
    precip_nc=get_precip.output.precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_event",
)
w.add_rule(pluvial_events, rule_id="pluvial_events")

# %%
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=pluvial_events.output.event_yaml,
)
w.add_rule(sfincs_update, rule_id="sfincs_update")

# %%
sfincs_run = SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

print(w)

# %% Test the workflow
w.run(dryrun=True)

# %% Write the workflow to a Snakefile
w.to_snakemake("workflow_test.smk")

# %% Test round-trip from YAML to Workflow
w.to_yaml("workflow_test.yml")
print(Workflow.from_yaml("workflow_test.yml"))

# %% Clean up
os.unlink("workflow_test.yml")
os.unlink("workflow_test.smk")
os.unlink("workflow_test.config.yml")
