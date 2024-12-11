"""Run pluvial design events with existing SFINCS model."""

# %% Import packages
import os
import subprocess
from pathlib import Path

from hydroflows.log import setuplog
from hydroflows.methods.fiat import FIATBuild, FIATRun, FIATUpdateHazard
from hydroflows.methods.flood_adapt.setup_flood_adapt import SetupFloodAdapt
from hydroflows.methods.rainfall import (
    PluvialDesignEventsGPEX,
)
from hydroflows.methods.sfincs import (
    SfincsBuild,
    SfincsPostprocess,
    SfincsRun,
    SfincsUpdateForcing,
)
from hydroflows.utils.example_data import fetch_data
from hydroflows.workflow import Workflow, WorkflowConfig

if __name__ == "__main__":
    # Where the current file is located
    pwd = Path(__file__).parent

    # %% Fetch the global build data (uncomment to fetch data required to run the workflow)
    cache_dir = fetch_data(data="global-data")

    # %% General setup of workflow
    # Define variables
    name = "pluvial_risk"
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

    # %% Build the models
    # Sfincs build
    sfincs_build = SfincsBuild(
        region=w.get_ref("$config.region"),
        sfincs_root="models/sfincs",
        default_config=w.get_ref("$config.hydromt_sfincs_config"),
        data_libs=w.get_ref("$config.data_libs"),
        res=w.get_ref("$config.sfincs_res"),
        river_upa=w.get_ref("$config.river_upa"),
        plot_fig=w.get_ref("$config.plot_fig"),
    )
    w.add_rule(sfincs_build, rule_id="sfincs_build")

    # Fiat build
    fiat_build = FIATBuild(
        region=sfincs_build.output.sfincs_region,
        ground_elevation=sfincs_build.output.sfincs_subgrid_dep,
        fiat_root="models/fiat",
        data_libs=w.get_ref("$config.data_libs"),
        config=w.get_ref("$config.hydromt_fiat_config"),
        continent=w.get_ref("$config.continent"),
    )
    w.add_rule(fiat_build, rule_id="fiat_build")

    pluvial_events = PluvialDesignEventsGPEX(
        gpex_nc=conf.data_libs[0].parent / "gpex.nc",  # FIXME use hydromt.datacatalog
        region=sfincs_build.output.sfincs_region,
        event_root="data/events",
        rps=w.get_ref("$config.rps"),
        wildcard="pluvial_events",
    )
    w.add_rule(pluvial_events, rule_id="pluvial_events")

    # %% Update the sfincs model with pluviual events
    sfincs_update = SfincsUpdateForcing(
        sfincs_inp=sfincs_build.output.sfincs_inp,
        event_yaml=pluvial_events.output.event_yaml,
    )
    w.add_rule(sfincs_update, rule_id="sfincs_update")

    # %% Run the sfincs model
    sfincs_run = SfincsRun(
        sfincs_inp=sfincs_update.output.sfincs_out_inp,
        sfincs_exe=w.get_ref("$config.sfincs_exe"),
    )
    w.add_rule(sfincs_run, rule_id="sfincs_run")

    # %% Postprocesses SFINCS results
    sfincs_post = SfincsPostprocess(
        sfincs_map=sfincs_run.output.sfincs_map,
    )
    w.add_rule(sfincs_post, rule_id="sfincs_post")

    # %% Update FIAT hazard
    fiat_update = FIATUpdateHazard(
        fiat_cfg=fiat_build.output.fiat_cfg,
        event_set_yaml=pluvial_events.output.event_set_yaml,
        map_type="water_level",
        hazard_maps=sfincs_post.output.sfincs_zsmax,
        risk=w.get_ref("$config.risk"),
    )
    w.add_rule(fiat_update, rule_id="fiat_update")

    # Run FIAT
    fiat_run = FIATRun(
        fiat_cfg=fiat_update.output.fiat_out_cfg,
        fiat_exe=w.get_ref("$config.fiat_exe"),
    )
    w.add_rule(fiat_run, rule_id="fiat_run")

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
    #subprocess.run(["snakemake", "-n", "--rerun-incomplete"], cwd=case_root)
    # uncomment to run the workflow
    #subprocess.run(["snakemake", "-c", "1", "--rerun-incomplete"], cwd=case_root)
    #
