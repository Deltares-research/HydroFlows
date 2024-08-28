# %% Import packages  # noqa: D100
import os

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
from hydroflows.workflow.workflow_config import WorkflowConfig

# %% Create a workflow config

conf = WorkflowConfig(
    region="setup_data/region.gpkg",
    data_libs="setup_data/data_catalog.yml",
    setup_scenario="global_setup_models",
    models_root_folder="models",
    data_root_folder="data",
    sim_subfolder="design_events",
    hydromt_sfincs_config="hydromt_config/sfincs_build_global.yaml",
    hydromt_fiat_config="hydromt_config/fiat_build_global.yaml",
    res=50,
    rps=[2, 10, 100],
    river_upa=10,
    continent="South America",
    risk=True,
    start_date="1990-01-01",
    end_date="2023-12-31",
    plot_fig=True,
    depth_min=0.05,
    sfincs_exe="../bin/sfincs/sfincs.exe",
    fiat_exe="../bin/fiat/fiat.exe",
)

# %% Create a workflow
w = Workflow(config=conf)

sfincs_build = SfincsBuild(
    region=w.get_ref("$config.region"),
    sfincs_root=os.path.join(
        conf.setup_scenario,
        conf.models_root_folder,
        "sfincs",
    ),
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
    fiat_root=os.path.join(
        conf.setup_scenario,
        conf.models_root_folder,
        "fiat",
    ),
    data_libs=w.get_ref("$config.data_libs"),
    config=w.get_ref("$config.hydromt_fiat_config"),
    continent=w.get_ref("$config.continent"),
)

w.add_rule(fiat_build, rule_id="fiat_build")

# %%
get_precip = GetERA5Rainfall(
    region=sfincs_build.output.sfincs_region,
    data_root=os.path.join(
        conf.setup_scenario,
        conf.data_root_folder,
        conf.sim_subfolder,
        "input",
    ),
    start_date=w.get_ref("$config.start_date"),
    end_date=w.get_ref("$config.end_date"),
)
w.add_rule(get_precip, rule_id="get_precip")

# %%
pluvial_events = PluvialDesignEvents(
    precip_nc=get_precip.output.precip_nc,
    event_root=os.path.join(
        conf.setup_scenario,
        conf.data_root_folder,
        conf.sim_subfolder,
        "events",
        "rainfall",
    ),
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_event",
)
w.add_rule(pluvial_events, rule_id="pluvial_events")

# %%
sfincs_update = SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    sim_subfolder=w.get_ref("$config.sim_subfolder"),
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
    hazard_root=os.path.join(
        conf.setup_scenario,
        conf.data_root_folder,
        conf.sim_subfolder,
        "output",
        "hazard",
    ),
)

w.add_rule(sfincs_postprocess, rule_id="sfincs_postprocess")

# %%
fiat_update_hazard = FIATUpdateHazard(
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml=pluvial_events.output.event_set_yaml,
    sim_subfolder=w.get_ref("$config.sim_subfolder"),
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

# %%
