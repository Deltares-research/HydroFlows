import json
from pathlib import Path

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
    params = ScriptParams(
        script=Path("script.py"), param1="value1", param2={"a": 1, "b": 2}
    )
    assert params.script == Path("script.py")
    assert params.param1 == "value1"
    assert params.param2 == {"a": 1, "b": 2}


def test_script_input_output():
    # test input with various options
    input = ScriptInput(test=Path("input.txt"))
    assert input.test == Path("input.txt")
    input = ScriptInput.model_validate(Path("input.txt"))
    assert input.input == Path("input.txt")
    input = ScriptInput.model_validate([Path("input1.txt"), Path("input2.txt")])
    assert input.input1 == Path("input1.txt")
    assert input.input2 == Path("input2.txt")
    input = ScriptInput.model_validate(
        {"foo": Path("input1.txt"), "bar": Path("input2.txt")}
    )
    assert input.foo == Path("input1.txt")
    assert input.bar == Path("input2.txt")
    # output inherits from input, only test if new attribute with output name is added
    output = ScriptOutput.model_validate(Path("output.txt"))
    assert output.output == Path("output.txt")


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
        param1="value1",
        param2={"a": 1, "b": 2},
    )
    # test params, input and output
    assert method.params.script == script_path
    assert method.params.param1 == "value1"
    assert method.input.input2 == Path("input2.txt")
    assert method.output.json_path == output
    # run method and check if output file exists and contains the correct data
    method.run()
    assert output.is_file()
    with open(output, "r") as f:
        data = json.load(f)
    assert data == method.to_dict(posix_path=True)
