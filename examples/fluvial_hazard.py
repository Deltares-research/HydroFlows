"""Build a fluvial hazard workflow."""

# %% Import packages
import subprocess
from pathlib import Path

from hydroflows import Workflow
from hydroflows.log import setuplog
from hydroflows.methods.discharge import FluvialDesignEvents
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsDownscale,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.methods.wflow import (
    WflowBuild,
    WflowRun,
    WflowUpdateForcing,
)
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow.workflow_config import WorkflowConfig

if __name__ == "__main__":
    # Get current file location
    pwd = Path(__file__).parent
    # Setup logging
    logger = setuplog()

    # %% Define variables
    name = "fluvial_hazard"
    model_dir = "models"
    data_dir = "data"
    input_dir = "input"
    output_dir = "output"
    simu_dir = "simulations"

    # Fetch the global data
    cache_dir = fetch_data(data="global-data")

    # Setup the configuration
    conf = WorkflowConfig(
        region=Path(pwd, "data/build/region.geojson"),
        hydromt_sfincs_config=Path(pwd, "hydromt_config/sfincs_config.yml"),
        hydromt_wflow_config=Path(pwd, "hydromt_config/wflow_config.yml"),
        wflow_exe=Path(pwd, "bin/wflow/bin/wflow_cli.exe"),
        sfincs_exe=Path(pwd, "bin/sfincs/sfincs.exe"),
        data_libs=[Path(cache_dir, "data_catalog.yml")],
        start_date="2014-01-01",
        end_date="2021-12-31",
        rps=[2, 5, 10],
        sfincs_res=50,
        river_upa=10,
        depth_min=0.05,
        plot_fig=True,
    )
    w = Workflow(name="fluvial_hazard", config=conf)

    # %% Build SFINCS model
    sfincs_build = SfincsBuild(
        region=w.get_ref("$config.region"),
        sfincs_root=Path(model_dir, "sfincs"),
        default_config=w.get_ref("$config.hydromt_sfincs_config"),
        data_libs=w.get_ref("$config.data_libs"),
        res=w.get_ref("$config.sfincs_res"),
        river_upa=w.get_ref("$config.river_upa"),
        plot_fig=w.get_ref("$config.plot_fig"),
    )
    w.add_rule(sfincs_build, rule_id="sfincs_build")

    # %% Build wflow model
    wflow_build = WflowBuild(
        region=sfincs_build.output.sfincs_region,
        wflow_root=Path(model_dir, "wflow"),
        default_config=w.get_ref("$config.hydromt_wflow_config"),
        data_libs=w.get_ref("$config.data_libs"),
        gauges=Path(sfincs_build.params.sfincs_root, "gis", "src.geojson"),
        plot_fig=w.get_ref("$config.plot_fig"),
    )
    w.add_rule(wflow_build, rule_id="wflow_build")

    # %% Update forcing & run wflow model
    wflow_update = WflowUpdateForcing(
        wflow_toml=wflow_build.output.wflow_toml,
        data_libs=w.get_ref("$config.data_libs"),
        start_time=w.get_ref("$config.start_date"),
        end_time=w.get_ref("$config.end_date"),
    )
    w.add_rule(wflow_update, rule_id="wflow_update")

    # %% Run the wflow model
    wflow_run = WflowRun(
        wflow_toml=wflow_update.output.wflow_out_toml,
        wflow_bin=w.get_ref("$config.wflow_exe"),
    )
    w.add_rule(wflow_run, rule_id="wflow_run")

    # %% Derive fluvial design events
    fluvial_events = FluvialDesignEvents(
        discharge_nc=wflow_run.output.wflow_output_timeseries,
        rps=w.get_ref("$config.rps"),
        wildcard="fluvial_events",
        event_root=Path(data_dir, "events"),
        index_dim="Q_gauges_bounds",
    )
    w.add_rule(fluvial_events, rule_id="fluvial_events")

    # %% prepare sfincs models per event, run & postprocess
    sfincs_update = SfincsUpdateForcing(
        sfincs_inp=sfincs_build.output.sfincs_inp,
        sim_subfolder=simu_dir,
        event_yaml=fluvial_events.output.event_yaml,
    )
    w.add_rule(sfincs_update, rule_id="sfincs_update")

    # %% Run the Sfincs model(s)
    sfincs_run = SfincsRun(
        sfincs_inp=sfincs_update.output.sfincs_out_inp,
        sfincs_exe=w.get_ref("$config.sfincs_exe"),
    )
    w.add_rule(sfincs_run, rule_id="sfincs_run")

    # %% Postprocess the sfincs output
    sfincs_post = SfincsDownscale(
        sfincs_map=sfincs_run.output.sfincs_map,
        sfincs_subgrid_dep=sfincs_build.output.sfincs_subgrid_dep,
        depth_min=w.get_ref("$config.depth_min"),
        output_root=Path(output_dir, "hazard"),
        event_name="{fluvial_events}",
    )
    w.add_rule(sfincs_post, rule_id="sfincs_post")

    # %% Test the workflow
    w.run(dryrun=True)

    # %% Write the workflow to a Snakefile
    w.to_snakemake(f"cases/{name}/Snakefile", dryrun=True)

    # %%
    subprocess.run(["snakemake", "-n"], cwd=f"cases/{name}")
    # uncomment to run the workflow
    # subprocess.run(["snakemake", "-c 1"], cwd=f"cases/{name}")
