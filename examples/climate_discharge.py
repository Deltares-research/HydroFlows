"""Example file for future climate dischare."""

import subprocess
from pathlib import Path

from hydroflows import Workflow
from hydroflows.methods.climate import (
    ClimateFactorsGridded,
    ClimateStatistics,
    MergeDatasets,
)
from hydroflows.methods.wflow import WflowConfig
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow.workflow_config import WorkflowConfig

if __name__ == "__main__":
    # Set the parent directory
    pwd = Path(__file__).parent

    # %% Fetch the climate build data
    cmip6_dir = fetch_data(data="cmip6-data")

    # %% General setup of workflow
    # Define variables
    name = "climate_discharge"  # for now
    model_dir = "models"
    data_dir = "data"
    input_dir = f"{data_dir}/input"
    stats_dir = f"{input_dir}/stats"
    change_dir = f"{input_dir}/change"
    assemble_dir = f"{input_dir}/assemble"
    output_dir = f"{data_dir}/output"
    simu_dir = "simulations"

    # Fetch a pre-build wflow-model
    wflow_data_dir = fetch_data(
        data="wflow-model",
        output_dir=Path(pwd, "cases", name, model_dir, "wflow"),
        sub_dir=False,
    )
    wflow_model_dir = wflow_data_dir.relative_to(Path(pwd, "cases", name))

    # Setup the config file
    conf = WorkflowConfig(
        region=Path(wflow_data_dir, "staticgeoms", "region.geojson"),
        data_libs=[Path(cmip6_dir, "data_catalog.yml")],
        cmip6_models=[
            "NOAA-GFDL_GFDL-ESM4",
            "INM_INM-CM5-0",
            "CSIRO-ARCCSS_ACCESS-CM2",
        ],
        cmip6_scenarios=["ssp245", "ssp585"],
        historical=[[2000, 2010]],
        future_horizons=[[2050, 2060], [2090, 2100]],
        plot_fig=True,
    )

    # Create a workflow
    w = Workflow(config=conf)
    w.wildcards.set("models", w.get_ref("$config.cmip6_models").value)
    w.wildcards.set("scenarios", w.get_ref("$config.cmip6_scenarios").value)

    ## Add the rules
    # %% Add meteo future climate factors workflow rule
    hist_stats = ClimateStatistics(
        region=w.get_ref("$config.region"),
        data_libs=w.get_ref("$config.data_libs"),
        model="{models}",
        horizon=w.get_ref("$config.historical"),
        data_root=stats_dir,
    )
    w.add_rule(hist_stats, rule_id="hist_stats")

    fut_stats = ClimateStatistics(
        region=w.get_ref("$config.region"),
        data_libs=w.get_ref("$config.data_libs"),
        model="{models}",
        scenario="{scenarios}",
        horizon=w.get_ref("$config.future_horizons"),
        data_root=stats_dir,
    )
    w.add_rule(fut_stats, rule_id="fut_stats")

    change_factors = ClimateFactorsGridded(
        hist_stats.output.stats,
        fut_stats.output.stats,
        model="{models}",
        scenario="{scenarios}",
        horizon=w.get_ref("$config.future_horizons"),
        wildcard="horizons",
        data_root=change_dir,
    )
    w.add_rule(change_factors, rule_id="change_factors")

    assemble = MergeDatasets(
        change_factors.output.change_factors,
        scenario="{scenarios}",
        horizon="{horizons}",
        data_root=Path(wflow_model_dir, simu_dir, "default", "factors"),
    )
    w.add_rule(assemble, rule_id="assemble")

    adjust_config = WflowConfig(
        wflow_toml=wflow_data_dir / simu_dir / "default" / "wflow_sbm.toml",
        ri_input__grid_factors=assemble.output.merged,
        scenario="{scenarios}",
        horizon="{horizons}",
        wildcards=["horizon", "scenario"],
        dir_output="run_default/{scenarios}_{horizons}",
        data_root=Path(wflow_model_dir, simu_dir, "{scenarios}_{horizons}"),
    )
    w.add_rule(adjust_config, rule_id="adjust_config")

    #     wflow_run = WflowRun(
    # wflow_toml=adjust_config.output.wflow_out_toml,
    # run_method="script",
    # wflow_run_script=Path("c:/code/non_pr/hydroflows/hydroflows/methods/wflow/scripts/run_wflow_change_factors.jl"),
    # )
    # w.add_rule(wflow_run, rule_id="wflow_run")

    # %% Test the workflow
    w.run(dryrun=True)

    # %% Write the workflow to a Snakefile
    w.to_snakemake(Path(pwd, f"cases/{name}/snakefile.smk"))

    # %%
    subprocess.run(
        ["snakemake", "--unlock", "-s", "snakefile.smk"], cwd=Path(pwd, f"cases/{name}")
    )
    # uncomment to run the workflow
    # subprocess.run(["snakemake", "-c 2", "--rerun-incomplete"], cwd=f"cases/{name}")
