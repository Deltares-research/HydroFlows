"""Testing for Setup FloodAdapt rules."""
from pathlib import Path

import pandas as pd
import toml

import hydroflows.methods.flood_adapt.translate_events as events
import hydroflows.methods.flood_adapt.translate_FIAT as fiat
from hydroflows.methods.flood_adapt.setup_flood_adapt import SetupFloodAdapt

fa_event_config = toml.load(tmp_output_event.joinpath("probalistic_event.toml"))
assert fa_event_config["mode"] == "risk"
assert len(fa_event_config["frequency"]) == len(fa_event_config["subevent_name"])
assert fa_event_config["name"] == tmp_output_event.stem

# get single event files
events = fa_event_config["subevent_name"]
for event in events:
    event_config = toml.load(tmp_output_event.joinpath(event, f"{event}.toml"))
    event_config.extent()


def test_translate_fiat_model(tmp_base_model: Path, tmp_output_model: Path):
    fiat.translate_model(tmp_base_model, tmp_output_model)

    exposure = pd.read_csv(tmp_output_model.joinpath("exposure", "exposure.csv"))
    required_columns = [
        "object_id",
        "object_name",
        "primary_object_type",
        "secondary_object_type",
        "extract_method",
        "ground_flht",
        "ground_elvt",
        "max_damage_structure",
        "max_damage_content",
        "fn_damage_structure",
        "fn_damage_content",
    ]
    assert set(required_columns) in set(exposure.columns)

    # Check if the exposure data exists
    assert tmp_output_model.joinpath("geoms", "region.geojson").exists()

    # Check if the exposure data exists
    assert tmp_output_model.joinpath("exposure", "exposure.csv").exists()

    # Check if the vulnerability data exists
    assert tmp_output_model.joinpath(
        "vulnerability", "vulnerability_curves.csv"
    ).exists()

    # Check if the hazard folder exists
    assert tmp_output_model.joinpath("hazard").exists()

    # Check if the output data folder exists
    assert tmp_output_model.joinpath("output").exists()


def test_translate_events(tmp_event: Path, tmp_output_event: Path):
    events.translate_events(tmp_event, tmp_output_event)

    assert tmp_output_event.joinpath("probalistic_event.toml").exists()

    fa_event_config = toml.load(tmp_output_event.joinpath("probalistic_event.toml"))
    assert fa_event_config["mode"] == "risk"
    assert len(fa_event_config["frequency"]) == len(fa_event_config["subevent_name"])
    assert fa_event_config["name"] == tmp_output_event.stem

    # get single event files
    ## Check if all the csv files in the toml are also there as a file
    events = fa_event_config["subevent_name"]
    for event in events:
        event_config = toml.load(tmp_output_event.joinpath(event, f"{event}.toml"))
        event_dict_extend = event_config.extent()
        csv_files_config = []
        for forcing in event_dict_extend:
            if ".csv" in forcing:
                csv_files_config.append(forcing)
        csv_files = tmp_output_event.joinpath(event).glob("*.csv")
    assert csv_files_config == csv_files


def test_fa_setup(
    fiat_base_model_path: Path, sfincs_inp_path: Path, event_set_yaml_path: Path
):
    # Setup the rule
    rule = SetupFloodAdapt(
        fiat_base_model=fiat_base_model_path,
        sfincs_inp=sfincs_inp_path,
        event_set_yaml=event_set_yaml_path,
    )
    rule.run_with_checks()
