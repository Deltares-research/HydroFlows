import json
from pathlib import Path

import pytest

from hydroflows.methods.script.script_method import (
    ScriptMethod,
    ScriptParams,
)


@pytest.fixture
def script_path(tmp_path) -> Path:
    # write small script to file which reads json as argument and writes to file
    return Path(tmp_path, "valid_script.py")


def write_script(script_path: Path) -> None:
    with open(script_path, "w") as f:
        f.write(
            """# test script
import json
import sys

# read json from command line
data = json.loads(sys.argv[1])

# write json to file
with open(data["output"]["json_path"], "w") as f:
    json.dump(data, f)
"""
        )
    return None


@pytest.fixture
def valid_input():
    return [Path("input1.txt"), Path("input2.txt")]


def test_script_params():
    params = ScriptParams(
        script=Path("script.py"), param1="value1", param2={"a": 1, "b": 2}
    )
    assert params.script == Path("script.py")
    assert params.param1 == "value1"
    assert params.param2 == {"a": 1, "b": 2}


def test_script_method_run(script_path: Path):
    write_script(script_path)
    output = script_path.parent / "output.json"
    method = ScriptMethod(script=script_path, output=output)
    method.run()
    assert output.is_file()
    with open(output, "r") as f:
        data = json.load(f.read())
    assert data["output"]["json_path"] == output.as_posix()
