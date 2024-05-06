configfile: "workflow/snake_config/config.yaml"

# Unpack config
region_name = config["REGION"]
scenario_name = config["SCENARIO"]
rps = config["RPS"]

# Target rule
rule all:
    input:
        event_catalog = f"data/interim/{region_name}/{scenario_name}/discharge/design_events.yml"

rule wflow_update_forcing:
    input:
        wflow_toml = f"models/wflow/{region_name}/wflow_sbm.toml",

    params:
        start_time = "2010-02-03T00:00:00",
        end_time = "2010-02-09T00:00:00",

    output:
        wflow_toml = f"models/wflow/{region_name}/simulations/{scenario_name}/wflow_sbm.toml",

    shell:
        """
        hydroflows run \
        wflow_update_forcing \
        -i wflow_toml={input.wflow_toml} \
        -o wflow_toml={output.wflow_toml} \
        -p start_time={params.start_time} \
        -p end_time={params.end_time}
        """

rule wflow_run:
    input:
        wflow_toml = rules.wflow_update_forcing.output.wflow_toml

    params:
        wflow_bin = f"bin/wflow/wflow_cli/bin/wflow_cli.exe"

    output:
        wflow_output_timeseries = f"models/wflow/{region_name}/simulations/{scenario_name}/run_default/output_scalar.nc"

    shell:
        """
        hydroflows run \
        wflow_run \
        -i wflow_toml={input.wflow_toml} \
        -o wflow_output_timeseries={output.wflow_output_timeseries} \
        -p wflow_bin={params.wflow_bin}
        """

rule get_design_events:
    input:
        time_series_nc = rules.wflow_run.output.wflow_output_timeseries

    params:
        rps = rps

    output:
        event_catalog = f"data/interim/{region_name}/{scenario_name}/discharge/design_events.yml"

    shell:
        """
        hydroflows run \
        wflow_design_hydro \
        -i time_series_nc={input.time_series_nc} \
        -p rps="{params.rps}" \
        -o event_catalog={output.event_catalog}
        """
