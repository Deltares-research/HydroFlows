"""Testing for Setup FloodAdapt rules."""
from pathlib import Path

import pandas as pd
import toml

import hydroflows.methods.flood_adapt.translate_events as events
import hydroflows.methods.flood_adapt.translate_FIAT as fiat
from hydroflows.methods.flood_adapt.setup_flood_adapt import SetupFloodAdapt


def NestedDictValues(d):
    """
    Recursively yields all values from a nested dictionary.

    Parameters
    ----------
    d : dict
        The nested dictionary from which to extract values.

    Yields
    ------
    Any
        Each value found in the nested dictionary, including values in nested dictionaries.
    """
    for v in d.values():
        if isinstance(v, dict):
            yield from NestedDictValues(v)
        else:
            yield v


def test_fa_setup(fiat_cfg: Path, sfincs_inp: Path, event_set_yaml: Path):
    # Setup the rule
    rule = SetupFloodAdapt(
        fiat_cfg=fiat_cfg,
        sfincs_inp=sfincs_inp,
        event_set_yaml=event_set_yaml,
    )
    rule.run_with_checks()


def test_translate_fiat_model(fiat_tmp_model: Path):
    """
    Test the translate_fiat_model function.

    This function tests that the translate_fiat_model function can translate a FIAT model
    into the format expected by FloodAdapt.

    It checks that the required columns are present in the exposure CSV file, that the
    exposure data exists, that the vulnerability data exists, and that the output data
    folder exists.

    Parameters
    ----------
    fiat_tmp_model : Path
        The path to the temporary FIAT model.
    tmp_output_model : Path
        The path to the temporary translated model.
    """
    fn_output = fiat_tmp_model.joinpath("translated_fiat_model")
    fiat.translate_model(fiat_tmp_model, fn_output)

    exposure = pd.read_csv(fn_output.joinpath("exposure", "exposure.csv"))
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
    assert fn_output.joinpath("geoms", "region.geojson").exists()

    # Check if the exposure data exists
    assert fn_output.joinpath("exposure", "exposure.csv").exists()

    # Check if the vulnerability data exists
    assert fn_output.joinpath("vulnerability", "vulnerability_curves.csv").exists()

    # Check if the output data folder exists
    assert fn_output.joinpath("output").exists()


def test_translate_events(event_set_file: Path):
    """
    Test the translate_events function.

    This function tests that the translate_events function can translate a probabilistic
    event set into the format expected by FloodAdapt.

    It checks that the required columns are present in the exposure CSV file, that the
    exposure data exists, that the vulnerability data exists, and that the output data
    folder exists.

    Parameters
    ----------
    event_set_file : Path
        The path to the temporary event set.
    """
    fn_output = event_set_file.parent.joinpath("fa_event_set")
    name = event_set_file.stem
    events.translate_events(event_set_file.parent, fn_output, name)

    assert fn_output.joinpath(f"{name}.toml").exists()

    fa_event_config = fn_output.joinpath(name, f"{name}.toml")
    assert fa_event_config["mode"] == "risk"
    assert len(fa_event_config["frequency"]) == len(fa_event_config["subevent_name"])
    assert fa_event_config["name"] == name

    fa_event_config = toml.load(fn_output.joinpathname, f"{name}.toml")
    assert fa_event_config["mode"] == "risk"
    assert len(fa_event_config["frequency"]) == len(fa_event_config["subevent_name"])
    assert fa_event_config["name"] == name

    # Check if timeseries.csv per forcing exists
    event_names = fa_event_config["subevent_name"]
    for event in event_names:
        event_config = toml.load(fn_output.joinpath(name, event, f"{event}.toml"))
        dict_values = list(NestedDictValues(event_config))
        csv_files_forcings_config = [
            item.split(".")[0]
            for item in dict_values
            if isinstance(item, str) and item.endswith(".csv")
        ]
        csv_files_forcings = []
        for filename in Path(fn_output).joinpath(name, event).glob("*.csv"):
            csv_files_forcings.append(filename.stem)
    assert csv_files_forcings_config == csv_files_forcings
