# Unpack config
region_name = config["REGION"]
run_name = config["RUN_NAME"]

# Target rule
rule all:
    input:
        fiat_out = f"models/fiat/{region_name}/output/spatial.gpkg"

rule update_fiat:
    input:
        fiat_cfg = f"models/fiat/{region_name}/settings.toml",
        hazard_map = f"models/sfincs/{region_name}/< input files >"

    params:
        map_type = "water_depth"

    output:
        fiat_haz = f"models/fiat/{region_name}/hazard/hazard_map.nc"

    shell:
        """
        hydroflows run \
        fiat_update_hazard \
        -i fiat_cfg={input.fiat_cfg} \
        -i hazard_map={input.hazard_map} \
        -o fiat_haz={output.fiat_haz} \
        -p map_type={params.map_type}
        """

rule run_fiat:
    input:
        fiat_haz = rules.update_fiat.output.fiat_haz
        fiat_cfg = rules.update_fiat.input.fiat_cfg

    params:
        fiat_bin = f"bin/fiat/fiat_cli/fiat.exe"
        threads = 4

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
