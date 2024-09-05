import io
import os
import subprocess
from pathlib import Path
from typing import List, Union

import pytest
import yaml

from hydroflows.workflow import (
    Parameters,
    Ref,
    Rule,
    Workflow,
    WorkflowConfig,
)
from hydroflows.workflow.method import ExpandMethod, Method, ReduceMethod
from hydroflows.workflow.workflow import Wildcards


class TestMethodInput(Parameters):
    input_file1: Path
    input_file2: Path


class TestMethodOutput(Parameters):
    output_file1: Path
    output_file2: Path


class TestMethod(Method):
    name: str = "test_method"

    def __init__(self, input_file1: Path, input_file2: Path) -> None:
        self.input: TestMethodInput = TestMethodInput(
            input_file1=input_file1, input_file2=input_file2
        )
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
def w() -> Workflow:
    config = {"rps": [2, 50, 100]}
    wildcards = {"region": ["region1", "region2"]}
    return Workflow(name="wf_instance", config=config, wildcards=wildcards)


@pytest.fixture()
def workflow_yaml_dict():
    return {
        "config": {
            "input_file": "tests/_data/rio_region.geojson",
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
                    "first_file": "$rules.mock_expand_method.output.output_file",
                    "second_file": "$rules.mock_expand_method.output.output_file2",
                    "root": "$config.root",
                },
            },
        ],
    }


@pytest.fixture()
def mock_expand_method():
    return MockExpandMethod(input_file="test.yml", root="", events=["1", "2"])


def create_workflow_with_mock_methods(
    w: Workflow, root: Path | None = None, input_file="test.yml"
):
    # create initial input file for workflow
    if root:
        for wild_card in w.wildcards.get("region"):
            (root / wild_card).mkdir()
            with open(root / wild_card / input_file, "w") as f:
                yaml.dump(dict(test="test"), f)
    else:
        root = Path("./")

    mock_expand_method = MockExpandMethod(
        input_file=root / "{region}" / input_file,
        root=root / "{region}",
        events=["1", "2"],
        wildcard="event",
    )

    w.add_rule(method=mock_expand_method, rule_id="mock_expand_rule")

    mock_method = TestMethod(
        input_file1=w.get_ref("$rules.mock_expand_rule.output.output_file"),
        input_file2=w.get_ref("$rules.mock_expand_rule.output.output_file2"),
    )

    w.add_rule(mock_method, rule_id="mock_rule")

    mock_reduce_method = MockReduceMethod(
        first_file=w.get_ref("$rules.mock_rule.output.output_file1"),
        second_file=w.get_ref("$rules.mock_rule.output.output_file2"),
        root=root / "out_{region}",
    )

    w.add_rule(method=mock_reduce_method, rule_id="mock_reduce_rule")
    return w


def test_workflow_init(w: Workflow):
    assert isinstance(w.config, WorkflowConfig)
    assert isinstance(w.wildcards, Wildcards)
    assert w.name == "wf_instance"


def test_workflow_repr(w: Workflow, mock_expand_method):
    w.add_rule(method=mock_expand_method, rule_id="mock_expand_rule")
    repr_str = w.__repr__()
    assert "region1" in repr_str
    assert "region2" in repr_str
    assert "mock_expand_rule" in repr_str


def test_workflow_add_rule(w: Workflow, tmp_path):
    w = create_workflow_with_mock_methods(w)
    assert len(w.rules) == 3
    assert isinstance(w.rules[0], Rule)
    assert w.rules[0].rule_id == "mock_expand_rule"
    assert w.rules[1].rule_id == "mock_rule"
    assert w.rules[2].rule_id == "mock_reduce_rule"


def test_workflow_rule_from_kwargs(w: Workflow, mocker, mock_expand_method):
    mocked_Method = mocker.patch("hydroflows.workflow.Method.from_kwargs")
    mocked_Method.return_value = mock_expand_method
    kwargs = {"rps": "$config.rps"}
    w.add_rule_from_kwargs(
        method="mock_expand_method", kwargs=kwargs, rule_id="mock_rule"
    )
    assert w.rules[0].rule_id == "mock_rule"


def test_workflow_get_ref(w: Workflow, tmp_path):
    w = create_workflow_with_mock_methods(w, root=tmp_path)
    ref = w.get_ref("$config.rps")
    assert isinstance(ref, Ref)
    assert ref.value == w.config.rps

    ref = w.get_ref("$rules.mock_expand_rule.output.output_file")
    assert ref.value.relative_to(tmp_path).as_posix() == "{region}/{event}/file.yml"


def test_workflow_from_yaml(tmp_path, workflow_yaml_dict):
    test_yml = tmp_path / "test.yml"
    with open(test_yml, "w") as f:
        yaml.dump(workflow_yaml_dict, f, sort_keys=False)

    w = Workflow.from_yaml(test_yml)
    assert isinstance(w, Workflow)
    assert w.rules[0].rule_id == "mock_expand_method"
    assert w.rules[1].rule_id == "mock_reduce_method"
    assert isinstance(w.config, WorkflowConfig)
    assert w.config.input_file == "tests/_data/rio_region.geojson"

    test_yml = {
        "config": {"region": "data/test_region.geojson", "rps": [5, 10, 50]},
        "rules": [
            {"method": "sfincs_build", "kwargs": {"region": "$config.region"}},
            "method",
        ],
    }
    test_file = tmp_path / "test.yml"
    with open(test_file, "w") as f:
        yaml.dump(test_yml, f, sort_keys=False)

    with pytest.raises(ValueError, match="Rule 2 invalid: not a dictionary."):
        Workflow.from_yaml(test_file)

    test_yml["rules"] = [{"kwargs": {"region": "$config.region"}}]

    with open(test_file, "w") as f:
        yaml.dump(test_yml, f, sort_keys=False)

    with pytest.raises(ValueError, match="Rule 1 invalid: 'method' name missing."):
        Workflow.from_yaml(test_file)


def test_workflow_to_snakemake(w: Workflow, tmp_path):
    test_file = tmp_path / "test.yml"
    with open(test_file, "w") as f:
        yaml.dump({"data": "test"}, f)
    w = create_workflow_with_mock_methods(w, root=tmp_path, input_file=test_file)
    snake_file = tmp_path / "snake_file.smk"
    w.to_snakemake(snakefile=snake_file)
    assert "snake_file.config.yml" in os.listdir(tmp_path)
    assert "snake_file.smk" in os.listdir(tmp_path)
    subprocess.run(
        [
            "snakemake",
            "-s",
            str(snake_file),
            "--dry-run",
            "--configfile",
            (tmp_path / "snake_file.config.yml").as_posix(),
        ]
    ).check_returncode()


def test_workflow_to_yaml(tmp_path, workflow_yaml_dict):
    test_file = tmp_path / "test.yml"
    with open(test_file, "w") as f:
        yaml.dump(workflow_yaml_dict, f, sort_keys=False)
    w = Workflow.from_yaml(test_file)
    test_file2 = tmp_path / "test2.yml"
    w.to_yaml(test_file2)
    w2 = Workflow.from_yaml(test_file2)
    assert w.config == w2.config
    assert w.wildcards == w2.wildcards
    assert all(
        [
            w_rule.rule_id == w2_rule.rule_id
            for w_rule, w2_rule in zip(w.rules, w2.rules)
        ]
    )


def test_workflow_run(mocker, w, tmp_path):
    w = create_workflow_with_mock_methods(w, root=tmp_path)
    mock_stdout = mocker.patch("sys.stdout", new_callable=io.StringIO)
    w.run(dryrun=True, missing_file_error=True, tmpdir=tmp_path)
    captured_stdout = mock_stdout.getvalue()
    for rule in w.rules:
        assert rule.rule_id in captured_stdout

    # Run workflow without region wildcard
    w = Workflow(name="test_workflow")
    root = tmp_path / "test_root"
    root.mkdir()
    input_file = "test.txt"
    with open(root / input_file, "w") as f:
        f.write("")
    mock_expand_method = MockExpandMethod(
        input_file=root / input_file,
        root=root,
        events=["1", "2"],
        wildcard="event",
    )

    w.add_rule(method=mock_expand_method, rule_id="mock_expand_rule")
    mock_reduce_method = MockReduceMethod(
        first_file=w.get_ref("$rules.mock_expand_rule.output.output_file"),
        second_file=w.get_ref("$rules.mock_expand_rule.output.output_file2"),
        root=root,
    )
    w.add_rule(method=mock_reduce_method, rule_id="mock_reduce_rule")
    w.run(dryrun=True, missing_file_error=True)
