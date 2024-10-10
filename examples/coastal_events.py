"""Generate coastal events example."""

# %% Import modules
from pathlib import Path

from hydroflows.methods.coastal import (
    CoastalDesignEvents,
    GetGTSMData,
)
from hydroflows.workflow import Workflow, WorkflowConfig

if __name__ == "__main__":
    pass

    # %% Setup variables
    pwd = Path(__file__).parent
    name = "coastal_events"
    data_dir = "data"
    input_dir = "input"

    # Setup the configuration
    config = WorkflowConfig(
        region=Path(pwd, "data/build/region.geojson").as_posix(),
        data_libs="p:/11209169-003-up2030/data/WATER_LEVEL/data_catalog.yml",  # replace with pooch fetched data
        start_time="2014-01-01",
        end_time="2021-12-31",
        rps=[2, 5, 10],
    )

    w = Workflow(config=config)

    # %% Get the GTSM data
    get_gtsm_data = GetGTSMData(
        gtsm_catalog=w.get_ref("$config.data_libs"),
        start_time=w.get_ref("$config.start_time"),
        end_time=w.get_ref("$config.end_time"),
        region=w.get_ref("$config.region"),
        data_root=Path(data_dir, input_dir, "coastal"),
    )
    w.add_rule(get_gtsm_data, rule_id="get_gtsm_data")

    coastal_design_events = CoastalDesignEvents(
        surge_timeseries=get_gtsm_data.output.surge_nc,
        tide_timeseries=get_gtsm_data.output.tide_nc,
        bnd_locations=get_gtsm_data.output.bnd_locations,
        rps=w.get_ref("$config.rps"),
        event_root=Path(data_dir, "events", "coastal"),
    )
    w.add_rule(coastal_design_events, rule_id="coastal_design_events")

    # %%
    # coastal_design_events.run()
    # %%
    # wf.run()

    # %% Test the workflow
    w.run(dryrun=True)

    # %% Write to a snakemake workflow file
    w.to_snakemake(f"{name}/workflow.smk")
