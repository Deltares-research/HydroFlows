"""Test the Workflow class for building workflows in python."""
# %% Import packages
from hydroflows import Workflow
from hydroflows.methods import (
    GetERA5Rainfall,
    PluvialDesignEvents,
    SfincsBuild,
    SfincsRun,
    SfincsUpdateForcing,
)

# %% Create a workflow
w = Workflow(config=dict(sfincs_exe="bin/sfincs/sfincs.exe"))

w.add_rule(
    method=SfincsBuild(
        region=r"regions/region1.geojson",
    ),
)

w.add_rule(
    GetERA5Rainfall(
        region=w.get_ref("rules.sfincs_build.output.sfincs_region"),
    ),
    rule_id="get_precip",
)

w.add_rule(
    PluvialDesignEvents(
        # precip_nc=w.get_ref("rules.get_precip.output.precip_nc"),
        # without ref also works bur results in different smk file
        precip_nc=w.rules.get_precip.output.precip_nc,
        rps=[2, 50, 100],
    ),
    rule_id="pluvial_events",
)

sfincs_update = SfincsUpdateForcing(
    sfincs_inp=w.get_ref("rules.sfincs_build.output.sfincs_inp"),
    event_yaml=w.get_ref("rules.pluvial_events.output.event_yaml"),
)
w.add_rule(sfincs_update, rule_id="sfincs_update")


sfincs_run = SfincsRun(
    # sfincs_inp=w.get_ref("rules.sfincs_update.output.sfincs_out_inp"),
    # reference to the output of the sfincs_update rule
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("config.sfincs_exe"),
)
w.add_rule(sfincs_run, rule_id="sfincs_run")

print(w)

# %% Test the workflow
w.run(dryrun=True)

# %% Write the workflow to a Snakefile
w.to_snakemake("Snakefile")
