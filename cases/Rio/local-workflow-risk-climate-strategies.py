"""Script to generate workflow files for the flood risk assessment of the Rio case integrating local data."""

# %%
# Import packages
from pathlib import Path

from hydroflows import Workflow, WorkflowConfig
from hydroflows.log import setuplog
from hydroflows.methods import catalog, fiat, flood_adapt, rainfall, script, sfincs
from hydroflows.workflow.wildcards import resolve_wildcards

# Where the current file is located
pwd = Path(__file__).parent

# %%
# General setup of workflow
# Define variables
name = "local"
setup_root = Path(pwd, "setups", name)
# Setup the log file
setuplog(
    path=setup_root / "hydroflows-logger-risk-climate-strategies.log", level="DEBUG"
)

# %%
# Setup the config file and data libs
# Config
config = WorkflowConfig(
    # general settings
    region=Path(pwd, "data/region.geojson"),
    plot_fig=True,
    catalog_path_global=Path(pwd, "data/global-data/data_catalog.yml"),
    catalog_path_local=Path(pwd, "data/local-data/data_catalog.yml"),
    # sfincs settings
    sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
    depth_min=0.05,
    subgrid_output=True,  # sfincs subgrid output should exist since it is used in the fiat model
    # fiat settings
    hydromt_fiat_config=Path(setup_root, "hydromt_config/fiat_config.yml"),
    fiat_exe=Path(pwd, "bin/fiat_v0.2.1/fiat.exe"),
    risk=True,
    # design events settings
    rps=[5, 10, 100],
    start_date="1990-01-01",
    end_date="2023-12-31",
    # Climate rainfall scenarios settings (to be applied on the derived design events)
    # Dictionary where:
    # - Key: Scenario name (e.g., "current", "rcp45", "rcp85")
    # - Value: Corresponding temperature delta (dT) for each scenario
    scenarios_dict={
        "present": 0,  # No temperature change for the present (or historical) scenario
        "rcp45_2050": 1.2,  # Moderate emissions scenario with +1.2°C
        "rcp85_2050": 2.5,  # High emissions scenario with +2.5°C
    },
)

# Strategies settings
strategies = ["default", "reservoirs", "dredging"]
strategies_dict = {"strategies": strategies}

# %%
# Setup the workflow
w = Workflow(config=config, name=name, root=setup_root, wildcards=strategies_dict)

# %%
# Merge global and local data catalogs
merged_catalog_global_local = catalog.MergeCatalogs(
    catalog_path1=w.get_ref("$config.catalog_path_global"),
    catalog_path2=w.get_ref("$config.catalog_path_local"),
    merged_catalog_path=Path(pwd, "data/merged_data_catalog_local_global.yml"),
)
w.create_rule(merged_catalog_global_local, rule_id="merge_global_local_catalogs")

# %%
# Sfincs build
sfincs_build = sfincs.SfincsBuild(
    region=w.get_ref("$config.region"),
    sfincs_root="models/sfincs_{strategies}",
    config=Path(setup_root, "hydromt_config/sfincs_config_{strategies}.yml"),
    catalog_path=merged_catalog_global_local.output.merged_catalog_path,
    plot_fig=w.get_ref("$config.plot_fig"),
    subgrid_output=w.get_ref("$config.subgrid_output"),
)
w.create_rule(sfincs_build, rule_id="sfincs_build")

# %%
# Preprocess local FIAT data scripts (clip exposure & preprocess clipped exposure)

# Clip exposure datasets to the region of interest.
fiat_clip_exp = script.ScriptMethod(
    script=Path(pwd, "scripts", "clip_exposure.py"),
    # Note that the output paths/names are hardcoded in the scipt
    # These names are used in the hydromt_fiat config
    input={
        "region": Path(pwd, "data/region.geojson"),
    },
    output={
        "census": Path(pwd, "data/preprocessed-data/census2010.gpkg"),
        "building_footprints": Path(
            pwd, "data/preprocessed-data/building_footprints.gpkg"
        ),
        "entrances": Path(pwd, "data/preprocessed-data/entrances.gpkg"),
    },
)
w.create_rule(fiat_clip_exp, rule_id="fiat_clip_exposure")

# Preprocess clipped exposure
fiat_preprocess_clip_exp = script.ScriptMethod(
    script=Path(pwd, "scripts", "preprocess_exposure.py"),
    input={
        "census": fiat_clip_exp.output.census,
        "building_footprints": fiat_clip_exp.output.building_footprints,
        "entrances": fiat_clip_exp.output.entrances,
    },
    output={
        "preprocessed_data_catalog": Path(
            pwd, "data/preprocessed-data/data_catalog.yml"
        ),
    },
)
w.create_rule(fiat_preprocess_clip_exp, rule_id="fiat_preprocess_exposure")

# %%
# Merge the preprocessed data catalog with the merged global and local data catalog
merged_catalog_all = catalog.MergeCatalogs(
    catalog_path1=merged_catalog_global_local.output.merged_catalog_path,
    catalog_path2=fiat_preprocess_clip_exp.output.preprocessed_data_catalog,
    merged_catalog_path=Path(pwd, "data/merged_data_catalog_all.yml"),
)
w.create_rule(merged_catalog_all, rule_id="merge_all_catalogs")

# %%

# Fiat build
fiat_build = fiat.FIATBuild(
    region=resolve_wildcards(
        sfincs_build.output.sfincs_region, {"strategies": strategies[0]}
    ),
    ground_elevation=resolve_wildcards(
        sfincs_build.output.sfincs_subgrid_dep, {"strategies": strategies[0]}
    ),
    fiat_root="models/fiat_default",
    catalog_path=merged_catalog_all.output.merged_catalog_path,
    config=w.get_ref("$config.hydromt_fiat_config"),
)
w.create_rule(fiat_build, rule_id="fiat_build")

# %%
# Preprocess local precipitation data and get design events
# Preprocess precipitation
precipitation = script.ScriptMethod(
    script=Path(pwd, "scripts", "preprocess_local_precip.py"),
    # Note that the output path/filename is hardcoded in the scipt
    output={
        "precip_nc": Path(
            pwd, "data/preprocessed-data/output_scalar_resampled_precip_station11.nc"
        )
    },
)
w.create_rule(precipitation, rule_id="preprocess_local_rainfall")

# Derive desing pluvial events for the current conditions based on the preprocessed local precipitation
pluvial_design_events = rainfall.PluvialDesignEvents(
    precip_nc=precipitation.output.precip_nc,
    rps=w.get_ref("$config.rps"),
    wildcard="pluvial_design_events",
    event_root="events/default",
)
w.create_rule(pluvial_design_events, rule_id="get_pluvial_design_events")

# %%
# Climate rainfall scenarios events
scenarios_design_events = rainfall.FutureClimateRainfall(
    scenarios=w.get_ref("$config.scenarios_dict"),
    event_names=pluvial_design_events.params.event_names,
    event_set_yaml=pluvial_design_events.output.event_set_yaml,
    event_wildcard="pluvial_design_events",  # we overwrite the wildcard
    scenario_wildcard="scenarios",
    event_root="events",
)
w.create_rule(scenarios_design_events, rule_id="scenarios_pluvial_design_events")

# %%
# Update the sfincs model with pluvial events
sfincs_update = sfincs.SfincsUpdateForcing(
    sfincs_inp=sfincs_build.output.sfincs_inp,
    event_yaml=scenarios_design_events.output.future_event_yaml,
    output_dir=sfincs_build.output.sfincs_inp.parent / "simulations_{scenarios}",
)
w.create_rule(sfincs_update, rule_id="sfincs_update")

# %%
# Run the sfincs model
sfincs_run = sfincs.SfincsRun(
    sfincs_inp=sfincs_update.output.sfincs_out_inp,
    sfincs_exe=w.get_ref("$config.sfincs_exe"),
)
w.create_rule(sfincs_run, rule_id="sfincs_run")

# %%
# Downscale Sfincs output to inundation maps.
sfincs_down = sfincs.SfincsDownscale(
    sfincs_map=sfincs_run.output.sfincs_map,
    sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
    depth_min=w.get_ref("$config.depth_min"),
    output_root="output/hazard_{scenarios}_{strategies}",
)
w.create_rule(sfincs_down, rule_id="sfincs_downscale")

# %%
# Postprocesses SFINCS results
sfincs_post = sfincs.SfincsPostprocess(
    sfincs_map=sfincs_run.output.sfincs_map,
)
w.create_rule(sfincs_post, rule_id="sfincs_post")

# %%
# Update/run FIAT for the event set and visualize the results

# Update hazard
fiat_update = fiat.FIATUpdateHazard(
    fiat_cfg=fiat_build.output.fiat_cfg,
    event_set_yaml=scenarios_design_events.output.future_event_set_yaml,
    map_type="water_level",
    hazard_maps=sfincs_post.output.sfincs_zsmax,
    risk=w.get_ref("$config.risk"),
    output_dir=fiat_build.output.fiat_cfg.parent
    / "simulations_{scenarios}_{strategies}",
)
w.create_rule(fiat_update, rule_id="fiat_update")

# Run FIAT
fiat_run = fiat.FIATRun(
    fiat_cfg=fiat_update.output.fiat_out_cfg,
    fiat_exe=w.get_ref("$config.fiat_exe"),
)
w.create_rule(fiat_run, rule_id="fiat_run")

# Visualize FIAT results
fiat_visualize_risk = fiat.FIATVisualize(
    fiat_output_csv=fiat_run.output.fiat_out_csv,
    fiat_cfg=fiat_update.output.fiat_out_cfg,
    spatial_joins_cfg=fiat_build.output.spatial_joins_cfg,
    output_dir="output/risk_{scenarios}_{strategies}",
)
w.create_rule(fiat_visualize_risk, rule_id="fiat_visualize_risk")

# %%
# Prepare Sfincs models for FloodAdapt DataBase
prep_sfincs_models = flood_adapt.PrepSfincsModels(
    sfincs_inp=sfincs_run.output,
    output_dir="output/floodadapt/risk_{scenarios}_{strategies}",
)
w.create_rule(prep_sfincs_models, rule_id="prep_sfincs_models")

# %%
# Setup FloodAdapt
floodadapt_build = flood_adapt.SetupFloodAdapt(
    sfincs_inp=prep_sfincs_models.output.sfincs_out_inp,
    fiat_cfg=fiat_update.output.fiat_out_cfg,
    event_set_yaml="events/present/pluvial_design_events_present.yml",
    output_dir="output/floodadapt/database_prep",
)
w.create_rule(floodadapt_build, rule_id="floodadapt_build")
# %%
# run workflow
w.dryrun()

# %%
# to snakemake
w.to_snakemake("local-workflow-risk-climate-strategies.smk")
# %%
