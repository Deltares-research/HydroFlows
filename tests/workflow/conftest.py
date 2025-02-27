from pathlib import Path
from typing import List, Union

import pytest
import yaml

from hydroflows._typing import ListOfPath, WildcardPath
from hydroflows.workflow import Method, Parameters, Workflow
from hydroflows.workflow.method import ExpandMethod, ReduceMethod
from hydroflows.workflow.rule import Rule


class TestMethodInput(Parameters):
    input_file1: Path
    input_file2: Path


class TestMethodOutput(Parameters):
    output_file1: Path
    output_file2: Path


class TestMethodParams(Parameters):
    param: str | None = None
    out_root: Path
    default_param: str = "default_param"
    default_param2: str = "default_param2"


class TestMethod(Method):
    name: str = "test_method"

    def __init__(
        self,
        input_file1: Path,
        input_file2: Path,
        param: None | str = None,
        out_root: Path | None = None,
        default_param: str = "default_param",
        **params,
    ) -> None:
        self.input: TestMethodInput = TestMethodInput(
            input_file1=input_file1,
            input_file2=input_file2,
        )
        # NOTE: possible wildcards in the input file directory
        # are forwarded using the parent of the input file by default
        if out_root is None:
            out_root = self.input.input_file1.parent
        self.params: TestMethodParams = TestMethodParams(
            param=param,
            out_root=out_root,
        )
        self.output: TestMethodOutput = TestMethodOutput(
            output_file1=self.params.out_root / "output1",
            output_file2=self.params.out_root / "output2",
        )

    def run(self):
        with open(self.output.output_file1, "w") as f:
            f.write("")
        with open(self.output.output_file2, "w") as f:
            f.write("")


class ExpandMethodInput(Parameters):
    input_file: Path


class ExpandMethodOutput(Parameters):
    output_file: ListOfPath | WildcardPath
    output_file2: ListOfPath | WildcardPath


class ExpandMethodParams(Parameters):
    root: Path
    events: list[str]
    wildcard: str = "wildcard"


class MockExpandMethod(ExpandMethod):
    name: str = "mock_expand_method"

    def __init__(
        self,
        input_file: Path,
        root: Path,
        events: List[str],
        wildcard: str = "wildcard",
    ) -> None:
        self.input: ExpandMethodInput = ExpandMethodInput(input_file=input_file)
        self.params: ExpandMethodParams = ExpandMethodParams(
            root=root, events=events, wildcard=wildcard
        )
        wc = "{" + self.params.wildcard + "}"
        self.output: ExpandMethodOutput = ExpandMethodOutput(
            output_file=self.params.root / wc / "file.yml",
            output_file2=self.params.root / wc / "file2.yml",
        )
        self.set_expand_wildcard(wildcard, self.params.events)

    def run(self):
        self.check_input_output_paths(False)
        for _, output_file in self._output_paths:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                f.write("")


class DoubleExpandMethodParams(Parameters):
    root: Path
    wildcards: dict[str, List[str]]


class MockDoubleExpandMethod(ExpandMethod):
    name: str = "mock_double_expand_method"

    def __init__(
        self,
        input_file: Path,
        root: Path,
        wildcards: dict[str, List[str]],
    ) -> None:
        self.input: ExpandMethodInput = ExpandMethodInput(input_file=input_file)
        self.params: DoubleExpandMethodParams = DoubleExpandMethodParams(
            root=root, wildcards=wildcards
        )
        wc_keys = list(self.params.wildcards.keys())
        wc = "{" + "}_{".join(wc_keys) + "}"
        self.output: ExpandMethodOutput = ExpandMethodOutput(
            output_file=self.params.root / wc / "file.yml",
            output_file2=self.params.root / wc / "file2.yml",
        )
        for key, values in self.params.wildcards.items():
            self.set_expand_wildcard(key, values)

    def run(self):
        pass


class ReduceInput(Parameters):
    files: Union[WildcardPath, List[Path]]


class ReduceParams(Parameters):
    root: Path


class ReduceOutput(Parameters):
    output_file: Path


class MockReduceMethod(ReduceMethod):
    name: str = "mock_reduce_method"

    def __init__(self, files: Union[Path, List[Path]], root: Path) -> None:
        self.input: ReduceInput = ReduceInput(files=files)
        self.params: ReduceParams = ReduceParams(root=root)
        self.output: ReduceOutput = ReduceOutput(
            output_file=self.params.root / "output_file.yml"
        )

    def run(self):
        data = {
            "inputs": self.input.files,
        }
        with open(self.output.output_file, "w") as f:
            yaml.dump(data, f)


@pytest.fixture()
def test_method():
    return TestMethod(input_file1="test_file1", input_file2="test_file2", param="param")


def create_test_method(
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


@pytest.fixture()
def workflow() -> Workflow:
    config = {"rps": [2, 50, 100]}
    wildcards = {"region": ["region1", "region2"]}
    return Workflow(name="wf_instance", config=config, wildcards=wildcards)


@pytest.fixture()
def mock_expand_method():
    return MockExpandMethod(input_file="test.yml", root="", events=["1", "2"])


@pytest.fixture()
def rule(test_method, workflow):
    return Rule(method=test_method, workflow=workflow, rule_id="test_rule")


@pytest.fixture()
def w() -> Workflow:
    config = {"rps": [2, 50, 100]}
    wildcards = {"region": ["region1", "region2"]}
    return Workflow(name="wf_instance", config=config, wildcards=wildcards)


@pytest.fixture()
def workflow_yaml_dict():
    return {
        "config": {
            "input_file": "tests/_data/region.geojson",
            "events": ["1", "2", "3"],
            "root": "root",
        },
        "rules": [
            {
                "method": "mock_expand_method",
                "kwargs": {
                    "input_file": "$config.input_file",
                    "events": "$config.events",
                    "root": "$config.root",
                },
            },
            {
                "method": "mock_reduce_method",
                "kwargs": {
                    "files": "$rules.mock_expand_method.output.output_file",
                    "root": "$config.root",
                },
            },
        ],
    }
