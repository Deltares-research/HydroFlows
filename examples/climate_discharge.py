"""Example file for future climate dischare."""

import subprocess
from pathlib import Path

from hydroflows import Workflow
from hydroflows.methods.climate import (
    ClimateFactorsGridded,
    ClimateStatistics,
)
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow.workflow_config import WorkflowConfig

if __name__ == "__main__":
    # Set the parent directory
    pwd = Path(__file__).parent

    # %% Fetch the global build data
    cache_dir = fetch_data(data="cmip6-data")

    # %% General setup of workflow
    # Define variables
    name = "climate_discharge"  # for now
    model_dir = "models"
    data_dir = "data"
    input_dir = "data/input"
    output_dir = "data/output"
    simu_dir = "simulations"

    # Setup the config file
    conf = WorkflowConfig(
        region=Path(pwd, "data/build/region.geojson"),
        data_libs=[Path(cache_dir, "data_catalog.yml")],
        cmip6_models=[
            "NOAA-GFDL_GFDL-ESM4",
            "INM_INM-CM5-0",
            "CSIRO-ARCCSS_ACCESS-CM2",
        ],
        cmip6_scenarios=["ssp245", "ssp585"],
        historical=("2000", "2010"),
        future_horizon=[("2050", "2060"), ("2090", "2100")],
        plot_fig=True,
    )

    # Create a workflow
    w = Workflow(config=conf)
    w.wildcards.set("models", w.get_ref("$config.cmip6_models").value)
    w.wildcards.set("scenarios", w.get_ref("$config.cmip6_scenarios").value)
    w.wildcards.set("horizons", w.get_ref("$config.future_horizon").value)

    ## Add the rules
    # %% Add meteo future climate factors workflow rule
    hist_stats = ClimateStatistics(
        region=w.get_ref("$config.region"),
        data_libs=w.get_ref("$config.data_libs"),
        model="{models}",
        scenario="{scenarios}",
        horizon=w.get_ref("$config.historical"),
        data_root=input_dir,
    )
    w.add_rule(hist_stats, rule_id="hist_stats")

    fut_stats = ClimateStatistics(
        region=w.get_ref("$config.region"),
        data_libs=w.get_ref("$config.data_libs"),
        model="{models}",
        scenario="{scenarios}",
        horizon=w.get_ref("$config.future_horizon"),
        data_root=input_dir,
        historical=False,
    )
    w.add_rule(fut_stats, rule_id="fut_stats")

    change_factors = ClimateFactorsGridded(
        hist_stats.output.stats,
        fut_stats.output.stats,
        model="{models}",
        scenario="{scenarios}",
        horizon="{horizons}",
        data_root=output_dir,
    )
    w.add_rule(change_factors, rule_id="change_factors")

    # %% Test the workflow
    w.run(dryrun=True)

    # %% Write the workflow to a Snakefile
    w.to_snakemake(Path(pwd, f"cases/{name}/snakefile.smk"))

    # %%
    subprocess.run(["snakemake", "--unlock"], cwd=Path(pwd, f"cases/{name}"))
    # uncomment to run the workflow
    # subprocess.run(["snakemake", "-c 2", "--rerun-incomplete"], cwd=f"cases/{name}")
