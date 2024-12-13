"""Run pluvial design events with existing SFINCS model."""

# %% Import modules
from pathlib import Path

from hydroflows.methods.rainfall import GetERA5Rainfall, PluvialDesignEvents
from hydroflows.methods.sfincs import (
    SfincsBuild,
    # SfincsPostprocess,
    SfincsDownscale,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow import Workflow, WorkflowConfig

if __name__ == "__main__":
    # Where the file is currently located
    pwd = Path(__file__).parent

    # %% Fetch the build data
    cache_dir = fetch_data(data="global-data")

    # Variables
    name = "pluvial_multiple_regions"
    model_dir = "models"
    data_dir = "data"
    input_dir = "data/input"
    output_dir = "data/output"
    simu_dir = "simulations"

    # Setup the configuration
    conf = WorkflowConfig(
        config=Path(pwd, "hydromt_config/sfincs_config.yml"),
        data_libs=[Path(cache_dir, "data_catalog.yml")],
        sfincs_exe=Path(pwd, "../bin/sfincs_v2.1.1/sfincs.exe"),
        start_date="2014-01-01",
        end_date="2021-12-31",
        rps=[2, 5, 10],
    )

    # %% Setup the workflow
    w = Workflow(
        config=conf,
        wildcards={"region": ["region", "region2"]},
    )

    # %% Build the SFINCS models
    sfincs_build = SfincsBuild(
        region=Path(pwd, data_dir, "build", "{region}.geojson"),
        config=w.get_ref("$config.config"),
        sfincs_root=Path(model_dir, "sfincs", "{region}"),
        data_libs=w.get_ref("$config.data_libs"),
    )
    w.add_rule(sfincs_build, "sfincs_build")

    # %% Get Rainfall timeseries
    get_rainfall = GetERA5Rainfall(
        region=sfincs_build.output.sfincs_region,
        data_root=Path(input_dir, "{region}"),
        start_date=w.get_ref("$config.start_date"),
        end_date=w.get_ref("$config.end_date"),
    )
    w.add_rule(get_rainfall, rule_id="get_rainfall")

    # %% Derive pluvial events from rainfall data
    pluvial_events = PluvialDesignEvents(
        precip_nc=get_rainfall.output.precip_nc,
        event_root=Path(data_dir, "events", "{region}"),
        rps=w.get_ref("$config.rps"),
        wildcard="pluvial_events",
    )
    w.add_rule(pluvial_events, rule_id="pluvial_events")

    # %% Update the SFINCS models
    sfincs_update = SfincsUpdateForcing(
        sfincs_inp=sfincs_build.output.sfincs_inp,
        event_yaml=pluvial_events.output.event_yaml,
        event_name="{pluvial_events}",
    )
    w.add_rule(sfincs_update, rule_id="sfincs_update")

    # %% Run SFINCS model
    sfincs_run = SfincsRun(
        sfincs_inp=sfincs_update.output.sfincs_out_inp,
        sfincs_exe=w.get_ref("$config.sfincs_exe"),
    )
    w.add_rule(sfincs_run, rule_id="sfincs_run")

    # Post process the results from pluvial events
    # sfincs_post = SfincsPostprocess(
    #     sfincs_map=sfincs_run.output.sfincs_map,
    #     sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
    #     hazard_root=Path(output_dir, "{region}"),
    # )
    sfincs_post = SfincsDownscale(
        sfincs_map=sfincs_run.output.sfincs_map,
        sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
        output_root=Path(output_dir, "{region}"),
    )
    w.add_rule(sfincs_post, "sfincs_post")

    # %% Do a dry run of the workflow
    w.run(dryrun=True)

    # %% Save to a snakemake workflow file
    w.to_snakemake(f"cases/{name}/workflow.smk")
