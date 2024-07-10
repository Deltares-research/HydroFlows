from hydroflows.workflows.events import EventCatalog

configfile: "workflow/snake_config/config.yaml"

# Unpack config
region_name = config["REGION"]
#run_name = config["RUN_NAME"]
scenario_name = config["SCENARIO"]
depth_min = config["DEPTH_MIN"]

# starting point is three event catalogs, located in fixed positions, for water level, rainfall, discharge.
# TODO: in a more dynamic manner, these event catalogs should be parsed from chosen event sets, or even combinations
# of event sets from different drivers
event_catalog_ymls = [
    f"data/interim/{region_name}/{scenario_name}/rainfall/design_events.yml",
    f"data/interim/{region_name}/{scenario_name}/discharge/design_events.yml",
    f"data/interim/{region_name}/{scenario_name}/water_level/design_events.yml",
]
event_catalog = EventCatalog.from_yamls(event_catalog_ymls)
event_catalog_yml = f"data/interim/{region_name}/{scenario_name}/design_events_combined.yml"
event_catalog.to_yaml(event_catalog_yml)

events = event_catalog.event_names
# create a list of inputs to allow expansion
event_inputs = [event_catalog.get_event(event).forcings[0].path for event in event_catalog.events]

# function to retrieve forcings for each event
def get_event_forcing(wildcards):
    return event_inputs[wildcards.event]


# Target rule
rule all:
    input:
        event_catalog = f"results/{region_name}/hazard/{scenario_name}/hazard_maps.yml"

rule update_sfincs:
    input:
        sfincs_inp = "models/sfincs/{region_name}/sfincs.inp",
        forcing_csv = get_event_forcing,
        event_catalog = event_catalog_yml
    params:
        event_name = "{event}"
    output:
        sfincs_inp = "models/sfincs/{region_name}/simulations/{scenario_name}/{event}/sfincs.inp"
    shell:
        """
        hydroflows run \
        sfincs_update_forcing \
        -i sfincs_inp={input.sfincs_inp} \
        -i event_catalog={input.event_catalog} \
        -o sfincs_inp={output.sfincs_inp} \
        -p event_name={params.event_name} \
        """

rule run_sfincs:
    input:
        sfincs_inp = rules.update_sfincs.output.sfincs_inp,
    params:
        sfincs_exe = "bin/sfincs/sfincs.exe"
    output:
        sfincs_map = "models/sfincs/{region_name}/simulations/{scenario_name}/{event}/sfincs_map.nc"
    shell:
        """
        hydroflows run \
        sfincs_run \
        -i sfincs_inp={input.sfincs_inp} \
        -o sfincs_map={output.sfincs_map} \
        -p sfincs_exe={params.sfincs_exe} \
        """

rule post_process_sfincs:
    input:
        sfincs_inp = rules.update_sfincs.output.sfincs_inp,
        sfincs_map = rules.run_sfincs.output.sfincs_map,
        sfincs_dep = "models/sfincs/{region_name}/subgrid/dep_subgrid.tif"
    params:
        depth_min = depth_min
    output:
        sfincs_inun = "results/{region_name}/hazard/{scenario_name}/flood_depth_{event}.tif"
    shell:
        """
        hydroflows run \
        sfincs_postprocess \
        -i sfincs_inp={input.sfincs_inp} \
        -i sfincs_dep={input.sfincs_dep} \
        -o sfincs_inun={output.sfincs_inun} \
        -p depth_min={params.depth_min} \
        """

rule hazard_catalog:
    input:
        event_catalog = event_catalog_yml,
        depth_hazard_maps = expand(
            "results/{region_name}/hazard/{scenario_name}/flood_depth_{event}.tif",
            event=events,
            region_name=region_name,
            scenario_name=scenario_name,
            allow_missing=True
        )
    output:
        event_catalog = f"results/{region_name}/hazard/{scenario_name}/hazard_maps.yml"
    shell:
        """
        hydroflows run \
        hazard_catalog \
        -i event_catalog={input.event_catalog} \
        -i depth_hazard_maps="{input.depth_hazard_maps}" \
        -o event_catalog={output.event_catalog} \
        """
