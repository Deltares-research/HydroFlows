"""Run pluvial design events with existing SFINCS model."""

# %% Import packages
import os
from pathlib import Path

from hydroflows.log import setuplog
from hydroflows.methods.flood_adapt.setup_flood_adapt import SetupFloodAdapt
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow import Workflow, WorkflowConfig

if __name__ == "__main__":
    # Where the current file is located
    pwd = Path(__file__).parent

    # %% Fetch the global build data (uncomment to fetch data required to run the workflow)
    cache_dir = fetch_data(data="global-data")

    # %% General setup of workflow
    # Define variables
    name = "test_fa"
    case_root = Path(pwd, "cases", name)
    setuplog(path=case_root / "hydroflows.log", level="DEBUG")

    # Create the case directory
    case_root.mkdir(exist_ok=True, parents=True)
    os.chdir(case_root)

    # Setup the config file
    conf = WorkflowConfig(
        # general settings
        region=Path(pwd, "data/build/region.geojson"),
        data_libs=[Path(cache_dir, "data_catalog.yml")],
        start_date="2000-01-01",
        end_date="2021-12-31",
        plot_fig=True,
        # sfincs settings
        hydromt_sfincs_config=Path(pwd, "hydromt_config/sfincs_config.yml"),
        sfincs_exe=Path(pwd, "bin/sfincs_v2.1.1/sfincs.exe"),
        sfincs_res=50,
        river_upa=10,
        # fiat settings
        hydromt_fiat_config=Path(pwd, "hydromt_config/fiat_config.yml"),
        fiat_exe=Path(pwd, "bin/fiat_v0.2.0/fiat.exe"),
        continent="Europe",
        risk=True,
        # design events settings
        rps=[10, 100],
    )

    # %% Setup the workflow
    w = Workflow(config=conf)

    # %% Prepare FloodAdapt
    fa_run = SetupFloodAdapt(
        fiat_cfg=Path(case_root, "models/fiat/settings.toml"),
        sfincs_inp=Path(case_root, "models/sfincs/sfincs.inp"),
        event_set_yaml=Path(case_root, "data/events/pluvial_events.yml"),
    )
    w.add_rule(fa_run, rule_id="setup_flood_adapt")

    # %% run workflow
    w.run(dryrun=False)

    # %% to snakemake
    w.to_snakemake(Path(case_root, "Snakefile"))

    # %% subprocess to run snakemake
    # subprocess.run(["snakemake", "-n", "--rerun-incomplete"], cwd=case_root)
    # uncomment to run the workflow
    # subprocess.run(["snakemake", "-c", "1", "--rerun-incomplete"], cwd=case_root)
    #
