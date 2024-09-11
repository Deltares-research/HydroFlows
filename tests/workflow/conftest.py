from pathlib import Path
from typing import List, Union

import pytest
import yaml

from hydroflows.workflow import Method, Parameters, Workflow
from hydroflows.workflow.method import ExpandMethod, ReduceMethod


class TestMethodInput(Parameters):
    input_file1: Path
    input_file2: Path


class TestMethodOutput(Parameters):
    output_file1: Path
    output_file2: Path


class TestMethodParams(Parameters):
    param: str
    default_param: str = "default_param"


class TestMethod(Method):
    name: str = "test_method"

    def __init__(
        self, input_file1: Path, input_file2: Path, param: None | str = None
    ) -> None:
        self.input: TestMethodInput = TestMethodInput(
            input_file1=input_file1, input_file2=input_file2
        )
        if param:
            self.params: TestMethodParams = TestMethodParams(param=param)
        # NOTE: possible wildcards in the input file directory
        # are forwarded using the parent of the input file
        self.output: TestMethodOutput = TestMethodOutput(
            output_file1=self.input.input_file1.parent / "output1",
            output_file2=self.input.input_file2.parent / "output2",
        )

    def run(self):
        with open(self.output.output_file1, "w") as f:
            f.write("")
        with open(self.output.output_file2, "w") as f:
            f.write("")


class ExpandMethodInput(Parameters):
    input_file: Path


class ExpandMethodOutput(Parameters):
    output_file: Path
    output_file2: Path


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


class ReduceInput(Parameters):
    first_file: Union[Path, List[Path]]
    second_file: Union[Path, List[Path]]


class ReduceParams(Parameters):
    root: Path


class ReduceOutput(Parameters):
    output_file: Path


class MockReduceMethod(ReduceMethod):
    name: str = "mock_reduce_method"

    def __init__(self, first_file: Path, second_file: Path, root: Path) -> None:
        self.input: ReduceInput = ReduceInput(
            first_file=first_file, second_file=second_file
        )
        self.params: ReduceParams = ReduceParams(root=root)
        self.output: ReduceOutput = ReduceOutput(
            output_file=self.params.root / "output_file.yml"
        )

    def run(self):
        data = {
            "input1": self.input.first_file,
            "input2": self.input.second_file,
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