import logging
import os
import re

import pytest
from conftest import MockExpandMethod, TestMethod, create_test_method

from hydroflows.workflow import Method, Parameters


def test_method_param_props(test_method: TestMethod):
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


def test_method_repr(test_method: TestMethod):
    assert test_method.name in test_method.__repr__()
    assert test_method.__repr__().startswith("Method")


def test_method_to_kwargs(test_method: TestMethod):
    kwargs = test_method.to_kwargs()
    expected_kwargs = {
        "input_file1": "test_file1",
        "input_file2": "test_file2",
        "param": "param",
        "out_root": ".",
    }
    assert kwargs == expected_kwargs
    kwargs = test_method.to_kwargs(exclude_defaults=False)
    expected_kwargs["default_param"] = "default_param"
    expected_kwargs["default_param2"] = "default_param2"
    assert kwargs == expected_kwargs


def test_method_to_dict(test_method: TestMethod):
    out_dict = test_method.to_dict()
    assert out_dict == {
        "input": {"input_file1": "test_file1", "input_file2": "test_file2"},
        "output": {"output_file1": "output1", "output_file2": "output2"},
        "params": {"out_root": ".", "param": "param"},
    }


def test_method_from_kwargs():
    with pytest.raises(
        ValueError, match="Cannot initiate from Method without a method name"
    ):
        Method.from_kwargs()
    test_method = Method.from_kwargs("test_method", input_file1="test", input_file2="")
    assert isinstance(test_method, TestMethod)
    assert test_method.input.input_file1.as_posix() == "test"


def test_get_subclass():
    method_subclass = Method._get_subclass("test_method")
    assert issubclass(method_subclass, TestMethod)


def test_dryrun(tmp_path):
    test_method = create_test_method(root=tmp_path)
    test_method.dryrun()
    dir_files = os.listdir(tmp_path)
    assert "test_file1" in dir_files
    assert "test_file2" in dir_files
    assert "output1" in dir_files
    assert "output2" in dir_files


def test_run_with_checks(tmp_path):
    test_method = create_test_method(
        root=tmp_path,
    )
    test_method.run_with_checks()


def test_check_input_output_paths(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    test_method: TestMethod = create_test_method(root=tmp_path, write_inputs=False)
    with pytest.raises(
        FileNotFoundError,
        match=re.escape(
            f"Input file {test_method.name}.input.input_file1 not found: {test_method.input.input_file1}"
        ),
    ):
        test_method.check_input_output_paths()
    test_method.check_input_output_paths(missing_file_error=False)

    assert "input_file1" in caplog.text
    assert "test_file1" in caplog.text
    assert "input_file2" in caplog.text
    assert "test_file2" in caplog.text
    # check if files are written
    assert "test_file1" in os.listdir(tmp_path)
    assert "test_file2" in os.listdir(tmp_path)

    test_method = create_test_method(root=tmp_path)
    # Check if it runs without errors
    test_method.check_input_output_paths()


def test_output_paths(tmp_path):
    test_method = create_test_method(root=tmp_path)
    paths = test_method._output_paths
    assert isinstance(paths[0], tuple)
    assert paths[0][0] == "output_file1"
    assert paths[0][1] == tmp_path / "output1"


def test_check_output_exists(tmp_path):
    test_method = create_test_method(root=tmp_path, write_inputs=False)
    with pytest.raises(
        FileNotFoundError,
        match=re.escape(
            f"Output file {test_method.name}.output.output_file1 not found: {test_method.output.output_file1}"
        ),
    ):
        test_method.check_output_exists()


def test_set_expand_wildcards(tmp_path):
    input_file = tmp_path / "test"
    mock_expand_method = MockExpandMethod(
        input_file=input_file, root=tmp_path, events=["1", "2"]
    )
    assert mock_expand_method._expand_wildcards == {"wildcard": ["1", "2"]}


def test_expand_output_paths(tmp_path):
    input_file = tmp_path / "test"
    mock_expand_method = MockExpandMethod(
        input_file=input_file, root=tmp_path, events=["1", "2"]
    )

    output_paths = mock_expand_method._output_paths
    assert len(output_paths) == 4
    assert output_paths[0][1] == tmp_path / "1" / "file.yml"
    assert output_paths[3][1] == tmp_path / "2" / "file2.yml"
    mock_expand_method = MockExpandMethod(
        input_file=input_file, root=tmp_path, events=["1", "2", "3", "4"]
    )
    output_paths = mock_expand_method._output_paths
    assert len(output_paths) == 8


def test_expand_output_paths_outputs(tmp_path):
    input_file = tmp_path / "test"
    mock_expand = MockExpandMethod(
        input_file=input_file, root=tmp_path, events=["1", "2"]
    )
    mock_expand.expand_output_paths()
    assert mock_expand.output.to_dict() == {
        "output_file": [tmp_path / "1" / "file.yml", tmp_path / "2" / "file.yml"],
        "output_file2": [tmp_path / "1" / "file2.yml", tmp_path / "2" / "file2.yml"],
    }
