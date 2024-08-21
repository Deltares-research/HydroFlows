# %% Import packages  # noqa: D100
from hydroflows import Workflow
from hydroflows.methods import (
    FIATBuild,
    FIATRun,
    FIATUpdateHazard,
    GetERA5Rainfall,
    PluvialDesignEvents,
    SfincsBuild,
    SfincsPostprocess,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.workflow.workflow_config import WorkflowConfig

# %% Create a workflow config

conf = WorkflowConfig(
    region="region.gpkg",
    data_libs="data_catalog.yml",
    hydromt_sfincs_config="hydromt_config/sfincs_build.yaml",
    hydromt_fiat_config="hydromt_config/fiat_build.yaml",
    res=50,
    rps=[1, 2, 5, 10, 20, 50, 100],
    river_upa=10,
    continent="south_america",
    risk=True,
    start_date="1990-01-01",
    end_date="2023-12-31",
    plot_fig=True,
    depth_min=0.05,
    sfincs_exe="bin/sfincs/sfincs.exe",
    fiat_exe="bin/fiat/fiat.exe",
)

# %% Create a workflow
w = Workflow(config=conf)

sfincs_build = SfincsBuild(
    region=w.get_ref("$config.region"),
    default_config=w.get_ref("$config.hydromt_sfincs_config"),
    data_libs=w.get_ref("$config.data_libs"),
    res=w.get_ref("$config.res"),
    river_upa=w.get_ref("$config.river_upa"),
    plot_fig=w.get_ref("$config.plot_fig"),
)
w.add_rule(sfincs_build, rule_id="sfincs_build")

# %%
fiat_build = FIATBuild(
    region=sfincs_build.output.sfincs_region,
    config=w.get_ref("$config.hydromt_fiat_config"),
    data_libs=w.get_ref("$config.data_libs"),
    continent=w.get_ref("$config.continent"),
)

w.add_rule(fiat_build, rule_id="fiat_build")

# %%
get_precip = GetERA5Rainfall(
    region=sfincs_build.output.sfincs_region,
    start_date=w.get_ref("$config.start_date"),
    end_date=w.get_ref("$config.end_date"),
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

# %%
sfincs_postprocess = SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
    sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
    depth_min=w.get_ref("$config.depth_min"),
)

w.add_rule(sfincs_postprocess, rule_id="sfincs_postprocess")

# %%
fiat_update_hazard = FIATUpdateHazard(
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml=pluvial_events.output.event_set_yaml,
    hazard_maps=sfincs_postprocess.output.hazard_tif,
    risk=w.get_ref("$config.risk"),
)

w.add_rule(fiat_update_hazard, rule_id="fiat_update_hazard")

# %%
fiat_run = FIATRun(
    fiat_cfg=fiat_update_hazard.output.fiat_out_cfg,
    fiat_bin=w.get_ref("$config.fiat_exe"),
)

w.add_rule(fiat_run, rule_id="fiat_run")

# %% Test the workflow
w.run(dryrun=True)

# %% Write the workflow to a Snakefile
w.to_snakemake("pluvial_design_events_workflow.smk")
