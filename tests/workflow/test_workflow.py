import io
import os
from pathlib import Path
from typing import List

import pytest
import yaml

from hydroflows.workflow import (
    Parameters,
    Ref,
    Rule,
    Workflow,
    WorkflowConfig,
)
from hydroflows.workflow.method import ExpandMethod, ReduceMethod


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
        self.input = ExpandMethodInput(input_file=input_file)
        self.params = ExpandMethodParams(root=root, events=events, wildcard=wildcard)
        wc = "{" + wildcard + "}"
        self.output = ExpandMethodOutput(
            output_file=self.params.root / f"{wc}.yml",
            output_file2=self.params.root / f"{wc}_2.yml",
        )
        self.set_expand_wildcards(wildcard, self.params.events)

    def run(self):
        for event in self.params.events:
            fmt_dict = {self.params.wildcard: event}
            event_file = Path(str(self.output.output_file).format(**fmt_dict))
            test_data = {event: "test"}
            with open(event_file, "w") as f:
                yaml.dumps(test_data, f)
        with open(self.output.output_file2, "w") as f:
            yaml.dumps({"test_file": "2nd_test_file"}, f)


class ReduceInput(Parameters):
    first_file: Path
    second_file: Path


class ReduceParams(Parameters):
    root: Path


class ReduceOutput(Parameters):
    output_file: Path


class MockReduceMethod(ReduceMethod):
    name: str = "mock_reduce_method"

    def __init__(self, first_file: Path, second_file: Path, root: Path) -> None:
        self.input = ReduceInput(first_file=first_file, second_file=second_file)
        self.params = ReduceParams(root=root)
        self.output = ReduceOutput(output_file=root / "output_file.yml")

    def run(self):
        data = {
            "input1": self.input.first_file,
            "input2": self.input.second_file,
            "name": self.params.name,
        }
        with open(self.output.output_file, "w") as f:
            yaml.dumps(data, f)


@pytest.fixture
def w():
    config = {"rps": [2, 50, 100]}
    wildcards = {"region": ["region1", "region2"]}
    return Workflow(name="wf_instance", config=config, wildcards=wildcards)


@pytest.fixture
def workflow_yaml_dict():
    return {
        "config": {
            "input_file": "tests/_data/rio_region.geojson",
            "events": [1, 2, 3],
            "root": "",
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
                    "first_input_file": "$rules.mock_expand_method.output.output_file",
                    "second_input_file": "$rules.mock_expand_method.output.output_file2",
                    "root": "$config.root",
                },
            },
        ],
    }


def get_workflow(workflow_yaml_dict, tmpdir):
    workflow_yaml_dict["config"]["root"] = tmpdir
    fp = tmpdir / "test.yml"
    with open(fp, "w") as f:
        yaml.dumps(workflow_yaml_dict, f, sort_keys=False)
    return Workflow.from_yaml(fp)


def test_workflow_init(w):
    assert isinstance(w.config, WorkflowConfig)
    assert isinstance(w.wildcards.wildcards, dict)
    assert w.name == "wf_instance"


def test_workflow_repr(w):
    mock_expand_method = MockExpandMethod(
        input_file="test.yml", root="", events=["1", "2"]
    )
    w.add_rule(method=mock_expand_method, rule_id="mock_expand_rule")
    repr_str = w.__repr__()
    assert "region1" in repr_str
    assert "region2" in repr_str
    assert "mock_expand_rule" in repr_str


def test_workflow_add_rule(w, mock_method):
    w.add_rule(method=mock_method, rule_id="mock_rule")
    w.add_rule(method=mock_method, rule_id="mock_rule2")
    assert len(w.rules) == 2
    assert isinstance(w.rules[0], Rule)
    assert w.rules[1].rule_id == "mock_rule2"


def test_workflow_rule_from_kwargs(w, mock_method, mocker):
    mocked_Method = mocker.patch("hydroflows.workflow.Method.from_kwargs")
    mocked_Method.return_value = mock_method
    kwargs = {"rps": "$config.rps"}
    w.add_rule_from_kwargs(method="mock_method", kwargs=kwargs, rule_id="mock_rule")
    assert w.rules[0].rule_id == "mock_rule"


def test_workflow_get_ref(w):
    ref = w.get_ref("$config.rps")
    assert isinstance(ref, Ref)
    assert ref.value == w.config.rps


def test_workflow_from_yaml(tmpdir, workflow):
    assert isinstance(workflow, Workflow)
    assert workflow.rules[0].rule_id == "sfincs_build"

    test_yml = {
        "config": {"region": "data/test_region.geojson", "rps": [5, 10, 50]},
        "rules": [
            {"method": "sfincs_build", "kwargs": {"region": "$config.region"}},
            "method",
        ],
    }
    test_file = os.path.join(tmpdir, "test.yml")
    with open(test_file, "w") as f:
        yaml.dump(test_yml, f, sort_keys=False)

    with pytest.raises(ValueError, match="Rule 2 invalid: not a dictionary."):
        Workflow.from_yaml(test_file)

    test_yml["rules"] = [{"kwargs": {"region": "$config.region"}}]

    with open(test_file, "w") as f:
        yaml.dump(test_yml, f, sort_keys=False)

    with pytest.raises(ValueError, match="Rule 1 invalid: 'method' name missing."):
        Workflow.from_yaml(test_file)


def test_workflow_to_snakemake(tmpdir, workflow):
    snakefile = os.path.join(tmpdir, "snakefile.smk")
    workflow.to_snakemake(snakefile)
    with open(snakefile, "r") as f:
        smk = f.read()
    assert "snakefile.config.yml" in smk
    smk = smk.replace("snakefile.config.yml", "sfincs_pluvial.config.yml")
    with open("examples/sfincs_pluvial.smk", "r") as f:
        smk2 = f.read()

    assert smk == smk2


def test_workflow_to_yaml(tmpdir, workflow):
    test_file = os.path.join(tmpdir, "test.yml")
    workflow.to_yaml(test_file)
    w2 = Workflow.from_yaml(test_file)
    assert workflow.config == w2.config
    assert workflow.wildcards == w2.wildcards
    assert all(
        [
            w_rule.rule_id == w2_rule.rule_id
            for w_rule, w2_rule in zip(workflow.rules, w2.rules)
        ]
    )


def test_workflow_run(mocker, workflow):
    mocker.patch("hydroflows.workflow.Rule.run")
    mock_stdout = mocker.patch("sys.stdout", new_callable=io.StringIO)
    workflow.run(dryrun=True)
    captured_stdout = mock_stdout.getvalue()
    assert "Running dryrun in /tmp/hydroflows_" in captured_stdout
    for rule in workflow.rules:
        assert rule.rule_id in captured_stdout
