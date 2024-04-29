configfile: "workflow/snake_config/config.yaml"

# Unpack config
region_file = config["REGION_FILE"]
region_name = config["REGION"]
data_libs = config["DATA_LIBS"]
river_upa = config["RIVER_UPA"]
plot_fig = config["PLOT_FIG"]

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
        data_libs = data_libs,
        res = 100,
        river_upa = river_upa,
        plot_fig = plot_fig

    output:
        sfincs_inp = f"models/sfincs/{region_name}/sfincs.inp",
        sfincs_region = f"models/sfincs/{region_name}/gis/region.geojson"

    shell:
        """
        hydroflows run \
        sfincs_build \
        -i region={input.region} \
        -o sfincs_inp={output.sfincs_inp} \
        -o sfincs_region={output.sfincs_region} \
        -p config={params.config} \
        -p data_libs="{params.data_libs}" \
        -p res={params.res}
        """


rule setup_fiat:
    input:
        region = rules.setup_sfincs.output.sfincs_region

    params:
        config = "workflow/hydromt_config/fiat_build.yaml",
        data_libs = data_libs,
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
        -p data_libs="{params.data_libs}" \
        -p continent={params.continent}
        """

rule setup_wflow:
    input:
        sfincs_region = rules.setup_sfincs.output.sfincs_region

    params:
        config = "workflow/hydromt_config/wflow_build.yaml",
        data_libs = data_libs,
        upstream_area = river_upa

    output:
        wflow_toml = f"models/wflow/{region_name}/wflow_sbm.toml"

    shell:
        """
        hydroflows run \
        wflow_build \
        -i sfincs_region={input.sfincs_region} \
        -o wflow_toml={output.wflow_toml} \
        -p config={params.config} \
        -p data_libs="{params.data_libs}"
        """
