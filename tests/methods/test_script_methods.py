import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hydroflows.methods.script.script_method import (
    ScriptInput,
    ScriptMethod,
    ScriptOutput,
    ScriptParams,
)


def write_script(script_path: Path) -> None:
    """Write a test script to the given path.

    The script reads json from the command line and writes it to a file.
    """
    with open(script_path, "w") as f:
        f.write(
            """# test script
import json
import sys

if __name__ == "__main__":
    # read json from command line
    data = json.loads(sys.argv[1])

    # write json to file
    with open(data["output"]["json_path"], "w") as f:
        json.dump(data, f)
"""
        )
    return None


def test_script_params():
    # test params
    params = ScriptParams(script=Path("script.py"), param1="value1", param2=2)
    assert params.script == Path("script.py")
    assert params.param1 == "value1"
    assert params.param2 == 2


def test_script_output():
    # test output with various options
    output = ScriptOutput(test="output.txt")
    assert output.test == Path("output.txt")  # test if converted to Path
    output = ScriptOutput.model_validate(Path("output.txt"))
    assert output.output == Path("output.txt")
    output = ScriptOutput.model_validate([Path("output1.txt"), Path("output2.txt")])
    assert output.output1 == Path("output1.txt")
    assert output.output2 == Path("output2.txt")
    output = ScriptOutput.model_validate(
        {"foo": Path("output1.txt"), "bar": Path("output2.txt")}
    )
    assert output.foo == Path("output1.txt")
    assert output.bar == Path("output2.txt")
    # test invalid output
    with pytest.raises(ValidationError):
        output = ScriptOutput(test=2)


def test_script_input():
    input = ScriptInput(input="input.txt")
    assert input.input == Path("input.txt")
    assert input.script is None
    input = ScriptInput(script="script.py")
    assert input.script == Path("script.py")
    ScriptInput.model_validate({})  # test empty input
    with pytest.raises(ValidationError):
        input = ScriptInput(script="script.py", foo=2)


def test_script_method_run(tmp_path: Path):
    # write script which parses json from command line and writes it to a file
    script_path = tmp_path / "valid_script.py"
    write_script(script_path)
    # create method
    output = script_path.parent / "output.json"
    method = ScriptMethod(
        script=script_path,
        output={"json_path": output},
        input=[Path("input1.txt"), Path("input2.txt")],
        params={"param1": "value1", "param2": 2},
    )
    # test params, input and output
    assert method.input.script == script_path
    assert method.params.param1 == "value1"
    assert method.input.input2 == Path("input2.txt")
    assert method.output.json_path == output
    # run method and check if output file exists and contains the correct data
    method.run()
    assert output.is_file()
    with open(output, "r") as f:
        data = json.load(f)
    assert data == json.loads(method.json_kwargs)

    # test optional input and params
    output2 = script_path.parent / "output2.json"
    method2 = ScriptMethod(script=script_path, output={"json_path": output2})
    method2.run()
    assert output2.is_file()
    with open(output2, "r") as f:
        data = json.load(f)
    assert data == json.loads(method2.json_kwargs)
