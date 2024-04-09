"""Testing for general Rule objects."""
import os

import pytest

from hydroflows.methods import FIATBuild
from hydroflows.rules import Rule


@pytest.fixture()
def eventstrings():
    return [
        "event_{:05d}".format(rp) for rp in [2, 5, 10, 20, 50, 100, 200, 500, 1000]
    ]

@pytest.fixture()
def regionstrings():
    return [
        "region_{:03d}".format(r) for r in range(10)
    ]

@pytest.fixture()
def region_path(tmpdir):
    p = os.path.join(tmpdir, "region.geojson")
    return p

@pytest.fixture()
def region_multi_path(tmpdir):
    p = os.path.join(tmpdir, "{region}.geojson")
    return p

@pytest.fixture()
def fiat_input(region_path):
    return {
        "region": region_path
    }

@pytest.fixture()
def fiat_region_inputs(region_multi_path):
    return {
        "region": region_multi_path
    }


@pytest.fixture()
def fiat_output(tmpdir):
    return {
        "fiat_cfg": os.path.join(tmpdir, "fiat_model", "settings.toml")
    }

@pytest.fixture()
def fiat_build_method():
    return FIATBuild

@pytest.fixture()
def fiat_event_outputs(tmpdir, eventstrings):
    return {
        "fiat_cfg": os.path.join(
            tmpdir,
            "fiat_model",
            "settings_{event}.toml"
        )
    }

@pytest.fixture()
def fiat_region_outputs(tmpdir, regionstrings):
    return {
        "fiat_cfg": os.path.join(
            tmpdir,
            "fiat_model_{region}",
            "settings.toml"
        )
    }


# TODO replace fiat_input for a set of inputs, including wflow, sfincs

@pytest.mark.parametrize(
    ("method", "input", "output"),
    [
        ( # case with single input and output
                pytest.lazy_fixture("fiat_build_method"),
                pytest.lazy_fixture("fiat_input"),
                pytest.lazy_fixture("fiat_output"),
        ),
        (  # case with single input and multiple outputs
                pytest.lazy_fixture("fiat_build_method"),
                pytest.lazy_fixture("fiat_input"),
                pytest.lazy_fixture("fiat_event_outputs"),
        ),
        (  # case with multi inputs and multi outputs (several regions)
                pytest.lazy_fixture("fiat_build_method"),
                pytest.lazy_fixture("fiat_input"),
                pytest.lazy_fixture("fiat_event_outputs"),
        ),
        # TODO: add a case where wildcard on input must be expanded to list input
        # TODO: not suitable for fiat build case. Suited e.g. for annual average loss
    ]
)
def test_rule_fiat(method, input, output):
    rule = Rule(
        method=method,
        input=input,
        output=output,
    )
    rule.validate_io()
