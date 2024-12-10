"""Generate coastal events example."""

# %% Import modules
import os
from pathlib import Path

from hydroflows.log import setuplog
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsUpdateForcing,
    SfincsRun,
)
from hydroflows.methods.coastal import (
    CoastalDesignEvents,
    GetGTSMData,
)
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow import Workflow, WorkflowConfig

if __name__ == "__main__":
    # Where the current file is located
    pwd = Path(__file__).parent

    cache_dir = fetch_data(data="global-data")

    # %% Setup variables
    name = "coastal_hazard"
    model_dir = "models"
    data_dir = "data"
    input_dir = "input"
    output_dir = "output"
    simu_dir = "simulations"

    case_root = Path(pwd, "cases", name)
    setuplog(path=case_root / "hydroflows.log", level="DEBUG")

    # Create the case directory
    case_root.mkdir(exist_ok=True, parents=True)
    os.chdir(case_root)

    # Setup the configuration
    config = WorkflowConfig(
        # General settings
        region=Path(pwd, "data/build/region.geojson"),
        gtsm_catalog=Path(cache_dir, "data_catalog.yml"),
        data_libs=[Path(cache_dir, "data_catalog.yml")],
        start_time="2014-01-01",
        end_time="2021-12-31",
        plot_fig=True,
        # sfincs settings
        hydromt_sfincs_config=Path(pwd, "hydromt_config/sfincs_config.yml"),
        sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
        sfincs_res=50,
        river_upa=10,
        # design events
        rps=[2, 5, 10],
    )

    w = Workflow(config=config)

    # %%

    sfincs_build = SfincsBuild(
        region=w.get_ref("$config.region"),
        sfincs_root=Path(model_dir,"sfincs"),
        default_config=w.get_ref("$config.hydromt_sfincs_config"),
        data_libs=w.get_ref("$config.data_libs"),
        res=w.get_ref("$config.sfincs_res"),
        river_upa=w.get_ref("$config.river_upa"),
        plot_fig=w.get_ref("$config.plot_fig")
    )

    w.add_rule(sfincs_build,rule_id="sfincs_build")

    # %% Get the GTSM data
    get_gtsm_data = GetGTSMData(
        gtsm_catalog=w.get_ref("$config.gtsm_catalog"),
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

    sfincs_update = SfincsUpdateForcing(
        sfincs_inp=sfincs_build.output.sfincs_inp,
        sim_subfolder=simu_dir,
        event_yaml=coastal_design_events.output.event_yaml
    )

    w.add_rule(sfincs_update, rule_id="sfincs_update")

    # %%
    
    sfincs_run = SfincsRun(
        sfincs_inp=sfincs_update.output.sfincs_out_inp,
        sfincs_exe=w.get_ref("$config.sfincs_exe")
    )

    w.add_rule(sfincs_run, rule_id="sfincs_run")
    # %% Test the workflow
    w.run(dryrun=True)

    # %% Write to a snakemake workflow file
    w.to_snakemake(f"cases/{name}/workflow.smk")
