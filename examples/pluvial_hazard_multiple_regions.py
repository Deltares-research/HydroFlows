"""Run pluvial design events with existing SFINCS model."""

# %% Import modules
from pathlib import Path

from hydroflows.methods.rainfall import GetERA5Rainfall, PluvialDesignEvents
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsPostprocess,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.workflow import Workflow, WorkflowConfig

if __name__ == "__main__":
    pass
    # %% Set the variables
    pwd = Path(__file__).parent
    name = "pluvial_multiple_regions"
    data_libs = Path(pwd, "data/global-data/data_catalog.yml").as_posix()

    # Setup the configuration
    conf = WorkflowConfig(
        start_date="",
        end_date="",
        rps=[5, 10],
    )

    # %% Setup the workflow
    w = Workflow(
        config=conf,
        wildcards={"region": ["region1", "region2"]},
    )

    # %% build sfincs models for each region

    sfincs_build = SfincsBuild(
        region="data/{region}.geojson",
        sfincs_root="models/sfincs/{region}",
    )
    w.add_rule(sfincs_build, "sfincs_build")

    # %% add rainfall methods

    get_rainfall = GetERA5Rainfall(
        region=sfincs_build.output.sfincs_region,
        data_root="data/{region}/rainfall/input",
        start_date="2000-01-01",
        end_date="2020-12-31",
    )
    w.add_rule(get_rainfall, rule_id="get_rainfall")

    pluvial_events = PluvialDesignEvents(
        precip_nc=get_rainfall.output.precip_nc,
        event_root="data/{region}/rainfall/events",
        rps=w.get_ref("$config.rps"),
        wildcard="event",
    )

    w.add_rule(pluvial_events, rule_id="pluvial_events")

    # %% add sfincs methods

    sfincs_pre = SfincsUpdateForcing(
        sfincs_inp=sfincs_build.output.sfincs_inp,
        event_yaml=pluvial_events.output.event_yaml,
        event_name="{event}",
    )
    w.add_rule(sfincs_pre, rule_id="sfincs_pre")

    sfincs_run = SfincsRun(
        sfincs_inp=sfincs_pre.output.sfincs_out_inp,
        sfincs_exe=w.get_ref("$config.sfincs_exe"),
    )
    w.add_rule(sfincs_run, rule_id="sfincs_run")

    sfincs_post = SfincsPostprocess(
        sfincs_map=sfincs_run.output.sfincs_map,
        sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
        hazard_root="data/{region}/output",
    )
    w.add_rule(sfincs_post, "sfincs_post")

    # %% run workflow
    w.run(dryrun=True)

    # %% to snakemake
    w.to_snakemake(f"{name}/workflow.smk")
