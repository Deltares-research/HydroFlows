configfile: "workflow/snake_config/config.yaml"

# unpack config
region_file = config["REGION_FILE"]
region_name = config["REGION"]
scenario_name = config["SCENARIO"]

rule all:
    input:
        event_catalog = f"data/interim/{region_name}/{scenario_name}/coastal/design_events.yml"

rule get_gtsm_data:
    input:
        region = region_file
    output:
        waterlevel_nc = "data/input/forcing_data/waterlevel.nc",
        surge_nc = "data/input/forcing_data/surge.nc",
    shell:
        """
        hydroflows run \
        get_gtsm_data \
        -i region={input.region} \
        -o waterlevel_nc={output.waterlevel_nc} \
        -o surge_nc={output.surge_nc}
        """

rule get_coast_rp:
    input:
        region = region_file,
        coastrp_fn = r"p:\11209169-003-up2030\data\WATER_LEVEL\COAST-RP\COAST-RP.nc"
    output:
        rps_nc = f"data/interim/{region_name}/{scenario_name}/forcing_data/waterlevel_rps.nc"
    shell:
        """
        hydroflows run \
        get_coast_rp \
        -i region={input.region} \
        -i coastrp_fn={input.coastrp_fn} \
        -o rps_nc={output.rps_nc}
        """

rule tide_surge_timeseries:
    input:
        waterlevel_timeseries = rules.get_gtsm_data.output.waterlevel_nc
    output:
        surge_timeseries = "data/input/forcing_data/surge_timeseries.nc",
        tide_timeseries = "data/input/forcing_data/tide_timeseries.nc",
    params:
        surge_timeseries = rules.get_gtsm_data.output.surge_nc
    shell:
        """
        hydroflows run \
        create_tide_surge_timeseries \
        -i waterlevel_timeseries={input.waterlevel_timeseries} \
        -o surge_timeseries={output.surge_timeseries} \
        -o tide_timeseries={output.tide_timeseries} \
        -p surge_timeseries={params.surge_timeseries}
        """

rule coastal_design_events:
    input:
        surge_timeseries = rules.tide_surge_timeseries.output.surge_timeseries,
        tide_timeseries = rules.tide_surge_timeseries.output.tide_timeseries,
        rps_nc = rules.get_coast_rp.output.rps_nc
    output:
        event_catalog = f"data/interim/{region_name}/{scenario_name}/coastal/design_events.yml"
    shell:
        """
        hydroflows run \
        coastal_design_events \
        -i surge_timeseries={input.surge_timeseries} \
        -i tide_timeseries={input.tide_timeseries} \
        -i rps_nc={input.rps_nc} \
        -o event_catalog={output.event_catalog} \
        """
