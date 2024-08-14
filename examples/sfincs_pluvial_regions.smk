# This file was generated by hydroflows version 0.1.0.dev

configfile: "sfincs_pluvial_regions.config.yml"

REGION=["test_region", "test_region2"]
EVENT=["p_event01", "p_event02"]

rule all:
    input:
        hazard_tif=expand("data/output/{region}/hazard/{event}.tif", region=REGION, event=EVENT),

rule sfincs_build:
    input:
        region="data/{region}.geojson",
    params:
        sfincs_root="models/sfincs/{region}",
        res=100.0,
    output:
        sfincs_inp="models/sfincs/{region}/sfincs.inp",
        sfincs_region="models/sfincs/{region}/gis/region.geojson",
        sfincs_subgrid_dep="models/sfincs/{region}/subgrid/dep_subgrid.tif",
    shell:
        """
        hydroflows method sfincs_build \
        region="{input.region}" \
        sfincs_root="{params.sfincs_root}" \
        res="{params.res}" \
        """

rule get_ERA5_rainfall:
    input:
        region=rules.sfincs_build.output.sfincs_region,
    params:
        data_input_root="data/input/{region}/rainfall",
    output:
        precip_nc="data/input/{region}/rainfall/era5_precip.nc",
    shell:
        """
        hydroflows method get_ERA5_rainfall \
        region="{input.region}" \
        data_input_root="{params.data_input_root}" \
        """

rule pluvial_design_events:
    input:
        precip_nc=rules.get_ERA5_rainfall.output.precip_nc,
    params:
        event_root="data/output/{region}/events",
        rps=config["rps"],
    output:
        event_yaml=expand("data/output/{{region}}/events/{event}.yml", event=EVENT),
        event_csv=expand("data/output/{{region}}/events/{event}.csv", event=EVENT),
        event_set="data/output/{region}/events/event_set.yml",
    shell:
        """
        hydroflows method pluvial_design_events \
        precip_nc="{input.precip_nc}" \
        event_root="{params.event_root}" \
        rps="{params.rps}" \
        """

rule sfincs_update_forcing:
    input:
        sfincs_inp=rules.sfincs_build.output.sfincs_inp,
        event_yaml=rules.pluvial_design_events.output.event_yaml,
    output:
        sfincs_out_inp="models/sfincs/{region}/simulations/{event}/sfincs.inp",
    shell:
        """
        hydroflows method sfincs_update_forcing \
        sfincs_inp="{input.sfincs_inp}" \
        event_yaml="{input.event_yaml}" \
        """

rule sfincs_run:
    input:
        sfincs_inp=rules.sfincs_update_forcing.output.sfincs_out_inp,
    params:
        sfincs_exe=config["sfincs_exe"],
    output:
        sfincs_map="models/sfincs/{region}/simulations/{event}/sfincs_map.nc",
    shell:
        """
        hydroflows method sfincs_run \
        sfincs_inp="{input.sfincs_inp}" \
        sfincs_exe="{params.sfincs_exe}" \
        """

rule sfincs_postprocess:
    input:
        sfincs_map=rules.sfincs_run.output.sfincs_map,
        sfincs_subgrid_dep=rules.sfincs_build.output.sfincs_subgrid_dep,
    params:
        hazard_root="data/output/{region}/hazard",
    output:
        hazard_tif="data/output/{region}/hazard/{event}.tif",
    shell:
        """
        hydroflows method sfincs_postprocess \
        sfincs_map="{input.sfincs_map}" \
        sfincs_subgrid_dep="{input.sfincs_subgrid_dep}" \
        hazard_root="{params.hazard_root}" \
        """
