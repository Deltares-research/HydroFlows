"""Testing for FIAT rules."""
from pathlib import Path

import pytest

from hydroflows.rules import FIATBuild


def test_fiat_build(tmpdir, region_path):
    # Setting input data
    input = {
        "region": region_path.as_posix(),
    }
    fn_fiat_cfg = Path(tmpdir, "fiat_model", "settings.toml")
    output = {
        "fiat_cfg": fn_fiat_cfg
    }

    # Setup the rule
    rule =  FIATBuild(input=input, output=output)
    rule.run()

    assert fn_fiat_cfg.exists()