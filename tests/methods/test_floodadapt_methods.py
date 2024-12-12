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


def test_translate_fiat_model(tmp_base_model: Path, tmp_output_model: Path):
    """
    Test the translate_fiat_model function.

    This function tests that the translate_fiat_model function can translate a FIAT model
    into the format expected by FloodAdapt.

    It checks that the required columns are present in the exposure CSV file, that the
    exposure data exists, that the vulnerability data exists, and that the output data
    folder exists.

    Parameters
    ----------
    tmp_base_model : Path
        The path to the temporary FIAT model.
    tmp_output_model : Path
        The path to the temporary translated model.
    """
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
    """
    Test the translate_events function.

    This function tests that the translate_events function can translate a probabilistic
    event set into the format expected by FloodAdapt.

    It checks that the required columns are present in the exposure CSV file, that the
    exposure data exists, that the vulnerability data exists, and that the output data
    folder exists.

    Parameters
    ----------
    tmp_event : Path
        The path to the temporary event set.
    tmp_output_event : Path
        The path to the temporary translated event set.
    """
    events.translate_events(tmp_event, tmp_output_event)

    assert tmp_output_event.joinpath("probalistic_event.toml").exists()

    fa_event_config = tmp_output_event.joinpath(
        "probabilistic_event", "probalistic_event.toml"
    )
    assert fa_event_config["mode"] == "risk"
    assert len(fa_event_config["frequency"]) == len(fa_event_config["subevent_name"])
    assert fa_event_config["name"] == tmp_output_event.stem

    tmp_output_event = Path(
        r"C:\Users\rautenba\repos\HydroFlows\examples\cases\pluvial_risk\flood_adapt_builder"
    )
    fa_event_config = toml.load(
        tmp_output_event.joinpath("probabilistic_set", "probabilistic_set.toml")
    )
    assert fa_event_config["mode"] == "risk"
    assert len(fa_event_config["frequency"]) == len(fa_event_config["subevent_name"])
    assert fa_event_config["name"] == "probabilistic_set"

    # Check if timeseries.csv per forcing exists
    event_names = fa_event_config["subevent_name"]
    for event in event_names:
        event_config = toml.load(
            tmp_output_event.joinpath("probabilistic_set", event, f"{event}.toml")
        )
        dict_values = list(NestedDictValues(event_config))
        csv_files_forcings_config = [
            item.split(".")[0]
            for item in dict_values
            if isinstance(item, str) and item.endswith(".csv")
        ]
        csv_files_forcings = []
        for filename in (
            Path(tmp_output_event).joinpath("probabilistic_set", event).glob("*.csv")
        ):
            csv_files_forcings.append(filename.stem)
    assert csv_files_forcings_config == csv_files_forcings


def test_fa_setup(
    fiat_cfg_path: Path, sfincs_inp_path: Path, event_set_yaml_path: Path
):
    # Setup the rule
    rule = SetupFloodAdapt(
        fiat_cfg=fiat_cfg_path,
        sfincs_inp=sfincs_inp_path,
        event_set_yaml=event_set_yaml_path,
    )
    rule.run_with_checks()
