"""Coastal events example."""
# %%
from hydroflows.methods.coastal import (
    CoastalDesignEvents,
    GetGTSMData,
)
from hydroflows.workflow import Workflow, WorkflowConfig

# %%
config = WorkflowConfig(
    region="data/test_region.geojson",
    data_root="data/input/coastal",
)

wf = Workflow(config=config)

get_gtsm_data = GetGTSMData(
    start_time="2000-01-01",
    end_time="2018-12-31",
    region=wf.get_ref("$config.region"),
    data_root=wf.get_ref("$config.data_root"),
)
wf.add_rule(get_gtsm_data, rule_id="get_gtsm_data")

coastal_design_events = CoastalDesignEvents(
    surge_timeseries=get_gtsm_data.output.surge_nc,
    tide_timeseries=get_gtsm_data.output.tide_nc,
    rps=[2, 10, 20],
    event_root="data/events/coastal",
)
wf.add_rule(coastal_design_events, rule_id="coastal_design_events")

print(wf)
# %%
coastal_design_events.run()
# %%
wf.run()

# %%
wf.to_yaml("coastal_events.yml")

# %%
wf.to_snakemake("coastal_events.smk")
