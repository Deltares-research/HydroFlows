"""Testing for misc. utils."""
from pathlib import Path

import pytest
import yaml

from hydroflows.utils.misc import adjust_config


@pytest.fixture()
def default_config(tmp_path):
    data = {
        "setup": "here",
        "arg1": True,
        "arg2": True,
        "kwargs": ["item1", "item2"],
        "meta": {"meta_item1": "some_meta"},
    }
    output_file = Path(tmp_path, "default_config.yml")
    with open(output_file, "w") as _w:
        yaml.dump(data, _w)

    return output_file


@pytest.fixture()
def extra_config(tmp_path):
    data = {
        "setup": "there",
        "arg2": False,
        "arg3": True,
    }
    output_file = Path(tmp_path, "extra_config.yml")
    with open(output_file, "w") as _w:
        yaml.dump(data, _w)

    return output_file


def test_adjust_config(tmp_path, default_config, extra_config):
    with open(default_config, "r") as _r:
        before = yaml.safe_load(_r)

    assert before["arg2"]
    assert before["setup"] == "here"
    assert "arg3" not in before
    assert "arg4" not in before

    adjust_config(default_config, extra_config, **{"arg4": False})

    with open(default_config, "r") as _r:
        after = yaml.safe_load(_r)

    assert not after["arg2"]
    assert after["setup"] == "there"
    assert after["arg3"]
    assert not after["arg4"]
