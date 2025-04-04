import glob
import logging
import os
import platform
import subprocess
from pathlib import Path

import pytest
import yaml

from hydroflows.workflow import (
    Rule,
    Workflow,
    WorkflowConfig,
)
from hydroflows.workflow.reference import Ref
from hydroflows.workflow.wildcards import Wildcards
from tests.workflow.conftest import (
    MockExpandMethod,
    MockReduceMethod,
    TestMethod,
)


def create_workflow_with_mock_methods(
    w: Workflow, root: Path | None = None, input_file="test.yml"
):
    # create initial input file for workflow
    if root:
        w.root = root
        root.mkdir(parents=True, exist_ok=True)
        with open(root / input_file, "w") as f:
            yaml.dump(dict(test="test"), f)
    else:
        root = Path("./")

    mock_expand_method = MockExpandMethod(
        input_file=input_file,
        root="{region}",
        events=["1", "2"],
        wildcard="event",
    )

    w.create_rule(method=mock_expand_method, rule_id="mock_expand_rule")

    mock_method = TestMethod(
        input_file1=mock_expand_method.output.output_file,
        input_file2=mock_expand_method.output.output_file2,
    )

    w.create_rule(mock_method, rule_id="mock_rule")

    mock_reduce_method = MockReduceMethod(
        files=mock_method.output.output_file1,
        root="out_{region}",
    )

    w.create_rule(method=mock_reduce_method, rule_id="mock_reduce_rule")
    return w


def test_workflow_init(workflow: Workflow):
    assert isinstance(workflow.config, WorkflowConfig)
    assert isinstance(workflow.wildcards, Wildcards)
    assert workflow.name == "wf_instance"


def test_workflow_repr(workflow: Workflow, mock_expand_method):
    workflow.create_rule(method=mock_expand_method, rule_id="mock_expand_rule")
    repr_str = workflow.__repr__()
    assert "region1" in repr_str
    assert "region2" in repr_str
    assert "mock_expand_rule" in repr_str


def test_workflow_create_rule(workflow: Workflow, tmp_path):
    w = create_workflow_with_mock_methods(workflow)
    assert len(w.rules) == 3
    assert isinstance(w.rules[0], Rule)
    assert w.rules[0].rule_id == "mock_expand_rule"
    assert w.rules[1].rule_id == "mock_rule"
    assert w.rules[2].rule_id == "mock_reduce_rule"


def test_workflow_rule_from_kwargs(workflow: Workflow, mocker, mock_expand_method):
    mocked_Method = mocker.patch("hydroflows.workflow.Method.from_kwargs")
    mocked_Method.return_value = mock_expand_method
    kwargs = {"rps": "$config.rps"}
    workflow.create_rule_from_kwargs(
        method="mock_expand_method", kwargs=kwargs, rule_id="mock_rule"
    )
    # TODO add check on input._ref dict if references are there
    assert workflow.rules[0].rule_id == "mock_rule"


def test_workflow_get_ref(workflow: Workflow, tmp_path):
    w = create_workflow_with_mock_methods(workflow, root=tmp_path)
    ref = w.get_ref("$config.rps")
    assert isinstance(ref, Ref)
    assert ref.value == w.config.rps

    ref = w.get_ref("$rules.mock_expand_rule.output.output_file")
    assert ref.value.as_posix() == "{region}/{event}/file.yml"


def test_workflow_from_yaml(tmp_path, workflow_yaml_dict):
    test_yml = tmp_path / "test.yml"
    with open(test_yml, "w") as f:
        yaml.dump(workflow_yaml_dict, f, sort_keys=False)

    w = Workflow.from_yaml(test_yml)
    assert isinstance(w, Workflow)
    assert w.rules[0].rule_id == "mock_expand_method"
    assert w.rules[1].rule_id == "mock_reduce_method"
    assert isinstance(w.config, WorkflowConfig)
    assert w.config.input_file == "tests/_data/region.geojson"

    test_yml = {
        "config": {
            "event_csv": "data/event.csv",
            "settings_toml": "model/settings.toml",
            "model_exe": "model/model.exe",
        },
        "rules": [
            {
                "method": "run_dummy_event",
                "kwargs": {
                    "event_csv": "$config.event_csv",
                    "settings_toml": "$config.settings_toml",
                    "model_exe": "$config.model_exe",
                    "output_dir": "output",
                },
            },
            "method",
        ],
    }
    test_file = tmp_path / "test.yml"
    with open(test_file, "w") as f:
        yaml.dump(test_yml, f, sort_keys=False)

    with pytest.raises(ValueError, match="Rule 2 invalid: not a dictionary."):
        Workflow.from_yaml(test_file)

    test_yml["rules"][0].pop("method")
    with open(test_file, "w") as f:
        yaml.dump(test_yml, f, sort_keys=False)

    with pytest.raises(ValueError, match="Rule 1 invalid: 'method' name missing."):
        Workflow.from_yaml(test_file)


def test_workflow_to_snakemake(workflow: Workflow, tmp_path, has_snakemake: bool):
    test_file = tmp_path / "test.yml"
    with open(test_file, "w") as f:
        yaml.dump({"data": "test"}, f)
    w = create_workflow_with_mock_methods(
        workflow, root=tmp_path, input_file=test_file.name
    )
    w.to_snakemake(snakefile="Snakefile")
    assert "Snakefile.config.yml" in os.listdir(tmp_path)
    assert "Snakefile" in os.listdir(tmp_path)
    if has_snakemake:
        subprocess.run(
            [
                "snakemake",
                "--dry-run",
            ],
            cwd=tmp_path,
        ).check_returncode()


def validate_cwl_files(cwl_folder: Path):
    for file in glob.glob((cwl_folder / "*.cwl").as_posix()):
        cmd = ["cwltool", "--validate", file]
        print(cmd)
        subprocess.run(cmd).check_returncode()


def validate_cwl_workflow(workflow_file: Path):
    config = workflow_file.with_suffix(".config.yml")
    subprocess.run(
        ["cwltool", "--validate", workflow_file.as_posix(), config.as_posix()]
    ).check_returncode()


@pytest.mark.skipif(platform.system() == "Windows", reason="Not supported on Windows")
def test_workflow_to_cwl(w: Workflow, tmp_path):
    test_file = tmp_path / "test.yml"
    with open(test_file, "w") as f:
        yaml.dump({"data": "test"}, f)
    w = create_workflow_with_mock_methods(w, root=tmp_path, input_file=test_file)
    cwl_file = tmp_path / "workflow.cwl"
    w.to_cwl(cwlfile=cwl_file)
    assert "workflow.cwl" in os.listdir(tmp_path)
    assert "workflow.config.yml" in os.listdir(tmp_path)
    validate_cwl_files(tmp_path / "cwl")
    validate_cwl_workflow(cwl_file)


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


def test_workflow_dryrun(mocker, workflow: Workflow, tmp_path: Path, caplog):
    caplog.set_level(logging.INFO)
    w = create_workflow_with_mock_methods(workflow, root=tmp_path)

    w.dryrun()

    for rule in w.rules:
        assert rule.rule_id in caplog.text

    # Run workflow without region wildcard


def test_workflow_run(tmp_path: Path):
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

    w.create_rule(method=mock_expand_method, rule_id="mock_expand_rule")
    mock_reduce_method = MockReduceMethod(
        files=w.get_ref("$rules.mock_expand_rule.output.output_file"),
        root=root,
    )
    w.create_rule(method=mock_reduce_method, rule_id="mock_reduce_rule")
    w.run()
