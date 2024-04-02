from pathlib import Path

from hydroflows.utils import compose_cli_list

# Unpack config
region_file = config["REGION_FILE"]
region_name = config["REGION"]
data_libs = compose_cli_list(config["DATA_LIBS"])

# Target rule
rule all:
    input:
        sfincs_inp = f"models/sfincs/{region_name}/sfincs.inp",
        fiat_cfg = f"models/fiat/{region_name}/settings.toml",
        wflow_toml = f"models/wflow/{region_name}/wflow_sbm.toml",

rule setup_sfincs:
    input:
        region = region_file

    params:
        config = "workflow/hydromt_config/sfincs_build.yaml",
        data_libs = data_libs, # FIXME how to pass a list?
        res = 100,

    output:
        sfincs_inp = f"models/sfincs/{region_name}/sfincs.inp",
        # This output is not defined in the method (it is not needed as an cli arguments), but is required to construct the desired DAG
        sfincs_src_points = f"models/sfincs/{region_name}/gis/src.geojson"

    shell:
        """
        hydroflows run \
        sfincs_build \
        -i region={input.region} \
        -o sfincs_inp={output.sfincs_inp} \
        -p config={params.config} \
        -p data_libs={params.data_libs} \
        -p res={params.res}
        """


rule setup_fiat:
    input:
        region = region_file

    params:
        config = "workflow/hydromt_config/fiat_build.yaml",
        data_libs = data_libs, # FIXME how to pass a list?
        continent = "europe",

    output:
        fiat_cfg = f"models/fiat/{region_name}/settings.toml"

    shell:
        """
        hydroflows run \
        fiat_build \
        -i region={input.region} \
        -o fiat_cfg={output.fiat_cfg} \
        -p config={params.config} \
        -p data_libs={params.data_libs} \
        -p continent={params.continent}
        """

rule setup_wflow:
    input:
        sfincs_src_points = f"models/sfincs/{region_name}/gis/src.geojson"

    params:
        config = "workflow/hydromt_config/wflow_build.yaml",
        # data_libs = data_libs, # FIXME how to pass a list?

    output:
        wflow_toml = f"models/wflow/{region_name}/wflow_sbm.toml"

    shell:
        """
        hydroflows run \
        wflow_build \
        -i sfincs_src_points={input.sfincs_src_points} \
        -o wflow_toml={output.wflow_toml} \
        -p config={params.config} \
        """
