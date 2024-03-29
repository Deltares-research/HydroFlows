# Unpack config
region_name = config["REGION"]
run_name = config["RUN_NAME"]

# Target rule
rule all:
    input:
        wflow_output_timeseries = f"models/wflow/{region_name}/simulations/{run_name}/run_default/output_scalar.nc"

rule update_wflow:
    input:
        wflow_toml = f"models/wflow/{region_name}/wflow_sbm.toml",

    params:
        start_time = "2010-02-03T00:00:00",
        end_time = "2010-02-09T00:00:00"
    output:
        wflow_toml = f"models/wflow/{region_name}/simulations/{run_name}/wflow_sbm.toml",

    shell:
        """
        hydroflows run \
        wflow_update_forcing \
        -i wflow_toml={input.wflow_toml} \
        -o wflow_toml={output.wflow_toml} \
        -p start_time={params.start_time} \
        -p end_time={params.end_time}
        """

rule run_wflow:
    input:
        wflow_toml = f"models/wflow/{region_name}/simulations/{run_name}/wflow_sbm.toml"

    params:
        wflow_bin = f"bin/wflow/wflow_cli/bin/wflow_cli.exe"

    output:
        wflow_output_timeseries = f"models/wflow/{region_name}/simulations/{run_name}/run_default/output_scalar.nc"

    shell:
        """
        hydroflows run \
        wflow_run \
        -i wflow_toml={input.wflow_toml} \
        -o wflow_output_timeseries={output.wflow_output_timeseries} \
        -p wflow_bin={params.wflow_bin}
        """

# rule post_process_wflow:
#     input:
#     output:
#     shell:
