from pathlib import Path

# Unpack config
project_root = Path(config["ROOT"])
region_file = project_root / config["REGION_FILE"]
region_name = config["REGION"]

# Target rule
rule all:
    input:
        sfincs_inp = str(project_root / "models" / "sfincs" / region_name / "sfincs.inp"),
        fiat_cfg = str(project_root / "models" / "fiat" / region_name / "settings.toml"),
        wflow_toml = str(project_root / "models" / "wflow" / region_name / "wflow_sbm.toml"),

rule setup_sfincs:
    # Inputs as per hydroflows method implementation
    input:
        region = str(region_file)

    # Outputs as per hydroflows method implementation
    output:
        sfincs_inp = str(project_root / "models" / "sfincs" / region_name / "sfincs.inp"),
        # This output is not defined in the method (it is not needed as an cli arguments), but is required to construct the desired DAG
        sfincs_src_points = str(project_root / "models" / "sfincs" / region_name / "gis" / "src.geojson")

    # Hydroflows CLI command. \" to escape any whitespace that might be in filepaths
    shell:
        "hydroflows run sfincs_build -i region=\"{input.region}\" -o sfincs_inp=\"{output.sfincs_inp}\""


rule setup_fiat:
    # Inputs as per hydroflows method implementation
    input:
        region = str(region_file)

    # Outputs as per hydroflows method implementation
    output:
        fiat_cfg = str(project_root / "models" / "fiat" / region_name / "settings.toml")

    # Hydroflows CLI command. \" to escape any whitespace that might be in filepaths
    shell:
        "hydroflows run fiat_build -i region=\"{input.region}\" -o fiat_cfg=\"{output.fiat_cfg}\""

rule setup_wflow:
    # Inputs as per hydroflows method implementation
    input:
        sfincs_src_points = str(project_root / "models" / "sfincs" / region_name / "gis" / "src.geojson")

    # Outputs as per hydroflows method implementation
    output:
        wflow_toml = str(project_root / "models" / "wflow" / region_name / "wflow_sbm.toml")

    # Hydroflows CLI command. \" to escape any whitespace that might be in filepaths
    shell:
        "hydroflows run wflow_build -i sfincs_src_points=\"{input.sfincs_src_points}\" -o wflow_toml=\"{output.wflow_toml}\""
