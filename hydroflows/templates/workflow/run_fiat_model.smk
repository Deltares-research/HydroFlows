# Unpack config
region_name = config["REGION"]
risk = config["RISK"]
scenario = config["SCENARIO"]
threads = config["THREADS"]

haz_fn = "hazard_map.nc"
if risk:
    haz_fn = "risk_map.nc"

# Target rule
rule all:
    input:
        fiat_out = f"models/fiat/{region_name}/output/spatial.gpkg"

rule update_fiat:
    input:
        fiat_cfg = f"models/fiat/{region_name}/settings.toml",
        event_catalog = f"results/{region_name}/hazard/{scenario}/hazard_maps.yml"

    params:
        map_type = "water_depth",
        risk = risk

    output:
        fiat_haz = f"models/fiat/{region_name}/hazard/{haz_fn}"

    shell:
        """
        hydroflows run \
        fiat_update_hazard \
        -i fiat_cfg={input.fiat_cfg} \
        -i event_catalog={input.event_catalog} \
        -o fiat_haz={output.fiat_haz} \
        -p map_type={params.map_type} \
        -p risk={params.risk}
        """

rule run_fiat:
    input:
        fiat_haz = rules.update_fiat.output.fiat_haz,
        fiat_cfg = rules.update_fiat.input.fiat_cfg

    params:
        fiat_bin = f"bin/fiat/fiat.exe",
        threads = threads

    output:
        fiat_out = f"models/fiat/{region_name}/output/spatial.gpkg"
    shell:
        """
        hydroflows run \
        fiat_run \
        -i fiat_haz={input.fiat_haz} \
        -i fiat_cfg={input.fiat_cfg} \
        -o fiat_out={output.fiat_out} \
        -p fiat_bin={params.fiat_bin} \
        -p threads={params.threads}
        """
