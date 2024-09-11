"""Workflow file for the Lagos case."""
# %%
# Import packages  # noqa: D100
import os

from hydroflows import Workflow
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
    WflowDesignHydro,
    WflowRun,
    WflowUpdateForcing,
)
from hydroflows.workflow.workflow_config import WorkflowConfig

# %%
if __name__ == "__main__":
    pass
    # %%
    ## General setup of workflow
    scenario = "global"  # for now

    conf = WorkflowConfig(
        region="data/build/region_small.geojson",
        data_libs="data/build/data_catalog.yml",
        model_dir="models",
        data_dir="data",
        simu_dir="design_events",
        hydromt_sfincs_config=f"hydromt_config/sfincs_{scenario}_config.yml",
        hydromt_wflow_config=f"hydromt_config/wflow_{scenario}_config.yml",
        hydromt_fiat_config=f"hydromt_config/fiat_{scenario}_config.yml",
        sfincs_res=50,
        wflow_res=0.0041667,
        rps=[5, 10, 25],
        river_upa=10,
        continent="Africa",
        risk=True,
        start_date="2020-01-01",
        end_date="2023-12-31",
        plot_fig=True,
        depth_min=0.05,
        wflow_exe="bin/wflow/bin/wflow_cli.exe",
        sfincs_exe="bin/sfincs/sfincs.exe",
        fiat_exe="bin/fiat/fiat.exe",
        # local_precip_path="preprocessed_data/output_scalar_resampled_precip_station11.nc",
    )

    # Create a workflow
    w = Workflow(config=conf)

    ## Build workflows
    # Sfincs build
    sfincs_build = SfincsBuild(
        region=w.get_ref("$config.region"),
        sfincs_root=os.path.join(
            conf.model_dir,
            "sfincs",
        ),
        default_config=w.get_ref("$config.hydromt_sfincs_config"),
        data_libs=w.get_ref("$config.data_libs"),
        res=w.get_ref("$config.sfincs_res"),
        river_upa=w.get_ref("$config.river_upa"),
        plot_fig=w.get_ref("$config.plot_fig"),
    )
    w.add_rule(sfincs_build, rule_id="sfincs_build")

    # Wflow build
    wflow_build = WflowBuild(
        region=sfincs_build.output.sfincs_region,
        wflow_root=os.path.join(
            conf.model_dir,
            "wflow",
        ),
        default_config=w.get_ref("$config.hydromt_wflow_config"),
        data_libs=w.get_ref("$config.data_libs"),
        gauges=os.path.join(sfincs_build.params.sfincs_root, "gis", "src.geojson"),
        plot_fig=w.get_ref("$config.plot_fig"),
    )

    w.add_rule(wflow_build, rule_id="wflow_build")

    # Fiat build
    fiat_build = FIATBuild(
        region=sfincs_build.output.sfincs_region,
        fiat_root=os.path.join(
            conf.model_dir,
            "fiat",
        ),
        data_libs=w.get_ref("$config.data_libs"),
        config=w.get_ref("$config.hydromt_fiat_config"),
        continent=w.get_ref("$config.continent"),
    )

    w.add_rule(fiat_build, rule_id="fiat_build")

    ## Update and run wflow + generate fluvial events
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
    fluvial_events = WflowDesignHydro(
        discharge_nc=wflow_run.output.wflow_output_timeseries,
        rps=w.get_ref("$config.rps"),
        wildcard="fluvial_event",
        event_root="data/events",
    )
    w.add_rule(fluvial_events, rule_id="fluvial_events")

    ## Pluvial events
    # Get the data
    if scenario == "global":
        get_precip = GetERA5Rainfall(
            region=sfincs_build.output.sfincs_region,
            data_root=os.path.join(
                conf.data_dir,
                conf.simu_dir,
                "input",
            ),
            start_date=w.get_ref("$config.start_date"),
            end_date=w.get_ref("$config.end_date"),
        )
        w.add_rule(get_precip, rule_id="get_precip")
        precip_nc = get_precip.output.precip_nc
    else:
        precip_nc = w.get_ref("$config.local_precip_path")

    # Actual derivation of events based on precip
    pluvial_events = PluvialDesignEvents(
        precip_nc=precip_nc,
        rps=w.get_ref("$config.rps"),
        wildcard="pluvial_event",
        event_root="data/events",
    )
    w.add_rule(pluvial_events, rule_id="pluvial_events")

    ## In between logic to combine fluvial and pluvial events into one set
    all_events = w.wildcards.get("pluvial_event") + w.wildcards.get("fluvial_event")
    w.wildcards.set("all_events", all_events)

    ## Updating, running and postprocessing SFINCS model
    # Sfincs update with precip
    sfincs_update = SfincsUpdateForcing(
        sfincs_inp=sfincs_build.output.sfincs_inp,
        sim_subfolder=w.get_ref("$config.simu_dir"),
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
        sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
        depth_min=w.get_ref("$config.depth_min"),
        hazard_root=os.path.join(
            conf.data_dir,
            conf.simu_dir,
            "output",
            "hazard",
        ),
        event_name="{all_events}",
    )
    w.add_rule(sfincs_post, rule_id="sfincs_post")

    ## Update and run FIAT
    # Set the combined event_set of both fluvial and pluvial
    w.wildcards.set("event_set", ["fluvial_events", "pluvial_events"])

    # Update hazard
    fiat_update = FIATUpdateHazard(
        fiat_cfg=fiat_build.output.fiat_cfg,
        event_set_yaml="data/events/{event_set}.yml",
        event_set_name="{event_set}",
        sim_subfolder=w.get_ref("$config.simu_dir"),
        hazard_maps=sfincs_post.output.hazard_tif,
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
    w.run(dryrun=True)

    # %% Write the workflow to a Snakefile
    w.to_snakemake(f"{scenario}_workflow.smk")

    # %%
