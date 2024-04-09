from datetime import datetime

# Unpack config
region_file = config["REGION_FILE"]
region_name = config["REGION"]
scenario_name = config["SCENARIO"]

# Target rule
rule all:
    input:
        event_catalog = f"interim/{region_name}/rainfall/{scenario_name}/design_events.yml"

rule get_ERA5_rainfall:
    input:
        sfincs_region = region_file

    params:
        start_date = "2010-02-03",
        end_date = "2010-02-09",

    output:
        time_series_nc = "input/forcing_data/era5_rainfall.nc"

    shell:
        """
        hydroflows run \
        get_ERA5_rainfall \
        -i sfincs_region={input.sfincs_region} \
        -o time_series_nc={output.time_series_nc} \
        -p start_date={params.start_date} \
        -p end_date={params.end_date}
        """

rule get_design_events:
    input:
        time_series_nc = rules.get_ERA5_rainfall.output.time_series_nc

    params:

    output:
        event_catalog = f"interim/{region_name}/rainfall/{scenario_name}/design_events.yml"

    shell:
        """
        hydroflows run \
        pluvial_design_hyeto \
        -i time_series_nc={input.time_series_nc} \
        -o event_catalog={ouput.event_catalog} \
        """
