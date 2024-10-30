"""Run pluvial design events with existing SFINCS model."""

# %% Import packages
from pathlib import Path

from fetch_data import fetch

from hydroflows.methods.rainfall import GetERA5Rainfall, PluvialDesignEvents
from hydroflows.methods.sfincs import SfincsRun, SfincsUpdateForcing
from hydroflows.workflow import Workflow, WorkflowConfig

if __name__ == "__main__":
    # Where the current file is located
    pwd = Path(__file__).parent

    # %% General setup of workflow
    # Define variables
    name = "pluvial_hazard"  # for now
    model_dir = "models"
    data_dir = "data"
    input_dir = "data/input"
    simu_dir = "simulations"
    sfincs_root = Path(model_dir, "sfincs")

    # Fetch the sfincs model
    fetch(data="sfincs-model", output_dir=Path(pwd, "cases", name, sfincs_root))

    # Setup the config file
    conf = WorkflowConfig(
        sfincs_exe=Path(pwd, "bin/sfincs/sfincs.exe"),
        start_date="2014-01-01",
        end_date="2021-12-31",
        rps=[2, 5, 10],
    )

    # %% Setup the workflow
    w = Workflow(config=conf)

    # %% Get precipitation data
    pluvial_data = GetERA5Rainfall(
        region=sfincs_root / "gis" / "region.geojson",
        data_root=input_dir,
        start_date=w.get_ref("$config.start_date"),
        end_date=w.get_ref("$config.end_date"),
    )
    w.add_rule(pluvial_data, rule_id="pluvial_data")

    # %% Derive pluviual events from precipitation data
    pluvial_events = PluvialDesignEvents(
        precip_nc=pluvial_data.output.precip_nc,
        event_root=Path(data_dir, "events"),
        rps=w.get_ref("$config.rps"),
        wildcard="pluvial_events",
    )
    w.add_rule(pluvial_events, rule_id="pluvial_events")

    # %% Update the sfincs model with pluviual events
    sfincs_update = SfincsUpdateForcing(
        sfincs_inp=sfincs_root / "sfincs.inp",
        sim_subfolder=simu_dir,
        event_yaml=pluvial_events.output.event_yaml,
    )
    w.add_rule(sfincs_update, rule_id="sfincs_update")

    # %% Run the sfincs model
    sfincs_run = SfincsRun(
        sfincs_inp=sfincs_update.output.sfincs_out_inp,
        sfincs_exe=w.get_ref("$config.sfincs_exe"),
    )
    w.add_rule(sfincs_run, rule_id="sfincs_run")

    # %% run workflow
    w.run(dryrun=True)

    # %% to snakemake
    w.to_snakemake(f"cases/{name}/workflow.smk")
