"""Testing for Setup FloodAdapt rules."""
from pathlib import Path

import pytest
import toml

import hydroflows.methods.flood_adapt.translate_events as events
from hydroflows.methods.flood_adapt.setup_flood_adapt import SetupFloodAdapt


def nested_dict_values(d):
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
            yield from nested_dict_values(v)
        else:
            yield v


@pytest.mark.requires_test_data()
def test_fa_setup(
    fiat_tmp_model: Path, sfincs_tmp_model: Path, event_set_file: Path, tmp_path: Path
):
    # Setup the rule
    """
    Test the SetupFloodAdapt rule.

    This function tests that the SetupFloodAdapt rule can run successfully, given a
    FIAT model, a SFINCS model, and an event set. It checks that the rule output is
    as expected, and that the output files can be read successfully.

    Parameters
    ----------
    fiat_tmp_model : Path
        The path to a temporary directory containing a FIAT model.
    sfincs_tmp_model : Path
        The path to a temporary directory containing a SFINCS model.
    event_set_file : Path
        The path to a file containing an event set, in the format expected by
        HydroFlows.
    """
    rule = SetupFloodAdapt(
        fiat_cfg=Path(fiat_tmp_model, "settings.toml"),
        sfincs_inp=Path(sfincs_tmp_model, "sfincs.inp"),
        event_set_yaml=event_set_file,
        output_dir=tmp_path.joinpath("flood_adapt"),
    )
    rule.run_with_checks()


@pytest.mark.requires_test_data()
def test_translate_events(event_set_file: Path, tmp_path: Path):
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
    fn_output = tmp_path.joinpath("fa_event_set")
    name = event_set_file.stem
    events.translate_events(event_set_file, fn_output, name)

    assert fn_output.joinpath(name, f"{name}.toml").exists()

    fa_event_config = toml.load(fn_output.joinpath(name, f"{name}.toml"))
    assert fa_event_config["mode"] == "risk"
    assert len(fa_event_config["frequency"]) == len(fa_event_config["subevent_name"])
    assert fa_event_config["name"] == name

    # Check if timeseries.csv per forcing exists
    event_names = fa_event_config["subevent_name"]
    for event in event_names:
        event_config = toml.load(fn_output.joinpath(name, event, f"{event}.toml"))
        dict_values = list(nested_dict_values(event_config))
        csv_files_forcings_config = [
            item.split(".")[0]
            for item in dict_values
            if isinstance(item, str) and item.endswith(".csv")
        ]
        csv_files_forcings = []
        for filename in Path(fn_output).joinpath(name, event).glob("*.csv"):
            csv_files_forcings.append(filename.stem)
    assert sorted(csv_files_forcings_config) == sorted(csv_files_forcings)
