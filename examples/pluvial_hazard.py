"""Run pluvial design events with existing SFINCS model."""

# %% Import packages
from pathlib import Path

from hydroflows.methods.rainfall import GetERA5Rainfall, PluvialDesignEvents
from hydroflows.methods.sfincs import SfincsRun, SfincsUpdateForcing
from hydroflows.workflow import Workflow, WorkflowConfig

if __name__ == "__main__":
    # Where the current file is located
    pwd = Path(__file__).parent

    # %% General setup of workflow
    # Define variables
    name = "pluvial_hazard"  # for now
    sfincs_root = Path("models/sfincs")
    case_root = Path(pwd, "cases", name)

    # %% Fetch the global build data (uncomment to fetch data required to run the workflow)
    # fetch(data="sfincs-model", output_dir=Path(pwd, "cases", name, sfincs_root))

    # Setup the config file
    config = WorkflowConfig(
        sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
        sfincs_inp=sfincs_root / "sfincs.inp",
        sfincs_region=sfincs_root / "gis" / "region.geojson",
        start_date="2014-01-01",
        end_date="2021-12-31",
        rps=[2, 5, 10],
    )

    # %% Setup the workflow
    w = Workflow(config=config)

    # %% Get precipitation data
    pluvial_data = GetERA5Rainfall(
        region=w.get_ref("$config.sfincs_region"),
        data_root="data/era5",
        start_date=w.get_ref("$config.start_date"),
        end_date=w.get_ref("$config.end_date"),
    )
    w.add_rule(pluvial_data, rule_id="pluvial_data")

    # %% Derive pluviual events from precipitation data
    pluvial_events = PluvialDesignEvents(
        precip_nc=pluvial_data.output.precip_nc,
        event_root="data/events",
        rps=w.get_ref("$config.rps"),
        wildcard="pluvial_events",
    )
    w.add_rule(pluvial_events, rule_id="pluvial_events")

    # %% Update the sfincs model with pluviual events
    sfincs_update = SfincsUpdateForcing(
        sfincs_inp=w.get_ref("$config.sfincs_inp"),
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
    w.dryrun(input_files=[config.sfincs_region, config.sfincs_inp])

    # %% to snakemake
    w.to_snakemake(Path(case_root, "Snakefile"))
