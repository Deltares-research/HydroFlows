import os
import re
from pathlib import Path
from pprint import pformat

import pytest
from mock_methods import TestMethod

from hydroflows.methods.fiat import FIATBuild
from hydroflows.workflow import Method, Parameters


@pytest.fixture()
def test_method():
    return TestMethod(input_file1="test_file1", input_file2="test_file2", param="param")


def create_method(
    root: Path,
    input_file1="test_file1",
    input_file2="test_file2",
    param="param",
    write_inputs=True,
) -> TestMethod:
    input_file1 = root / input_file1
    input_file2 = root / input_file2
    if write_inputs:
        for input_file in [input_file1, input_file2]:
            with open(input_file, "w") as f:
                f.write("")
    return TestMethod(input_file1=input_file1, input_file2=input_file2, param=param)


def test_method_param_props(test_method):
    with pytest.raises(ValueError, match="Input should be a Parameters instance"):
        test_method.input = "input param"
    with pytest.raises(ValueError, match="Output should be a Parameters instance"):
        test_method.output = "output param"
    with pytest.raises(ValueError, match="Params should be a Parameters instance"):
        test_method.params = "param"

    delattr(test_method, "_input")
    with pytest.raises(ValueError, match="Input parameters not set"):
        test_method.input  # noqa
    delattr(test_method, "_output")
    with pytest.raises(ValueError, match="Output parameters not set"):
        test_method.output  # noqa
    delattr(test_method, "_params")
    assert isinstance(test_method.params, Parameters)


def test_method_repr(test_method):
    assert test_method.name in test_method.__repr__()
    assert f"parameters={pformat(test_method.dict)}" in test_method.__repr__()


def test_method_to_kwargs(test_method):
    kwargs = test_method.to_kwargs()
    assert kwargs == {
        "input_file1": "test_file1",
        "input_file2": "test_file2",
        "param": "param",
    }
    kwargs = test_method.to_kwargs(exclude_defaults=False)
    assert kwargs == {
        "input_file1": "test_file1",
        "input_file2": "test_file2",
        "param": "param",
        "default_param": "default_param",
    }


def test_method_to_dict(test_method):
    out_dict = test_method.to_dict()
    assert out_dict == {
        "input": {"input_file1": "test_file1", "input_file2": "test_file2"},
        "output": {"output_file1": "output1", "output_file2": "output2"},
        "params": {"param": "param"},
    }


def test_method_from_dict(test_method):
    method_dict = test_method.to_dict()
    new_test_method = TestMethod.from_dict(
        input=method_dict["input"],
        output=method_dict["output"],
        params=method_dict["params"],
        name=test_method.name,
    )
    assert new_test_method == test_method


def test_method_from_kwargs():
    with pytest.raises(
        ValueError, match="Cannot initiate from Method without a method name"
    ):
        Method.from_kwargs()
    test_method = Method.from_kwargs("test_method", input_file1="test", input_file2="")
    assert isinstance(test_method, TestMethod)
    assert test_method.input.input_file1.as_posix() == "test"


def test_get_subclass():
    known_methods = [m.name for m in Method._get_subclasses()]

    with pytest.raises(
        ValueError,
        match=re.escape(f"Unknown method: fake_method, select from {known_methods}"),
    ):
        Method._get_subclass("fake_method")
    method_subclass = Method._get_subclass("fiat_build")
    assert issubclass(method_subclass, FIATBuild)


def test_dryrun(tmp_path):
    test_method = create_method(root=tmp_path)
    test_method.dryrun()
    dir_files = os.listdir(tmp_path)
    assert "test_file1" in dir_files
    assert "test_file2" in dir_files
    assert "output1" in dir_files
    assert "output2" in dir_files


def test_run_with_checks(tmp_path):
    test_method = create_method(
        root=tmp_path,
    )
    test_method.run_with_checks()


def test_check_input_output_paths(tmp_path, capsys):
    test_method: TestMethod = create_method(root=tmp_path, write_inputs=False)
    with pytest.raises(
        FileNotFoundError,
        match=re.escape(
            f"Input file {test_method.name}.input.input_file1 not found: {test_method.input.input_file1}"
        ),
    ):
        test_method.check_input_output_paths()
    test_method.check_input_output_paths(missing_file_error=False)
    captured = capsys.readouterr()
    assert "input_file1" in captured.out
    assert "test_file1" in captured.out
    assert "input_file2" in captured.out
    assert "test_file2" in captured.out
    # check if files are written
    assert "test_file1" in os.listdir(tmp_path)
    assert "test_file2" in os.listdir(tmp_path)

    test_method = create_method(root=tmp_path)
    # Check if it runs without errors
    test_method.check_input_output_paths()
