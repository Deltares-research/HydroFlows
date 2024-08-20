"""Coastal events example."""
# %%
from hydroflows.methods.coastal import (
    CoastalDesignEvents,
    GetCoastRP,
    GetGTSMData,
    TideSurgeTimeseries,
)
from hydroflows.workflow import Workflow, WorkflowConfig

# %%
conf = WorkflowConfig(
    region="data/test_region.geojson",
    data_root="data/input/coastal",
)

wf = Workflow(config=conf)

get_gtsm_data = GetGTSMData(
    region=wf.get_ref("$config.region"),
    data_root=wf.get_ref("$config.data_root"),
)
wf.add_rule(get_gtsm_data, rule_id="get_gtsm_data")

get_coast_rp = GetCoastRP(
    region=wf.get_ref("$config.region"),
    data_root=wf.get_ref("$config.data_root"),
)
wf.add_rule(get_coast_rp, rule_id="get_coast_rp")

tide_surge_timeseries = TideSurgeTimeseries(
    waterlevel_timeseries=wf.get_ref("get_gtsm_data.output.waterlevel_nc"),
    data_root=wf.get_ref("$config.data_root"),
)
wf.add_rule(tide_surge_timeseries, rule_id="tide_surge_timeseries")

coastal_design_events = CoastalDesignEvents(
    surge_timeseries=tide_surge_timeseries.output.surge_timeseries,
    tide_timeseries=tide_surge_timeseries.output.tide_timeseries,
    waterlevel_rps=get_coast_rp.output.rps_nc,
    event_root="data/events/coastal",
)

wf.add_rule(coastal_design_events, rule_id="coastal_design_events")

print(wf)

# %%
wf.run(dryrun=True)

# %%
wf.to_yaml("coastal_events.yml")

# %%
wf.to_snakemake("coastal_events.smk")
