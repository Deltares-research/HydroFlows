from pathlib import Path

project_root = Path(r"C:\Users\tromp_wm\OneDrive - Stichting Deltares\Documents\HydroFlows\artifact_project_folder")

rule all:
    input:
        sfincs_inp = str(project_root / "models" / "sfincs" / "artifact_region" / "sfincs.inp"),
        fiat_cfg = str(project_root / "models" / "fiat" / "artifact_region" / "settings.toml"),

rule setup_sfincs:
    input:
        region = str(project_root / "data" / "sfincs" / "input" / "artifact_region.geojson")
    output:
        sfincs_inp = str(project_root / "models" / "sfincs" / "artifact_region" / "sfincs.inp")
    shell:
        "hydroflows run sfincs_build -i region=\"{input.region}\" -o sfincs_inp=\"{output.sfincs_inp}\""


rule setup_fiat:
    input:
        region = str(project_root / "data" / "sfincs" / "input" / "artifact_region.geojson")
    output:
        fiat_cfg = str(project_root / "models" / "fiat" / "artifact_region" / "settings.toml")
    shell:
        "hydroflows run fiat_build -i region=\"{input.region}\" -o fiat_cfg=\"{output.fiat_cfg}\""
