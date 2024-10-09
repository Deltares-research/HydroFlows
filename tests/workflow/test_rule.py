import re
from pathlib import PosixPath
from weakref import ReferenceType

import pytest

from hydroflows.workflow import Rule
from hydroflows.workflow.rule import Rules
from tests.workflow.conftest import (
    ExpandMethodOutput,
    MockExpandMethod,
    MockReduceMethod,
    TestMethod,
)


@pytest.fixture()
def rule(test_method, workflow):
    return Rule(method=test_method, workflow=workflow, rule_id="test_rule")


def test_rule_init(rule, workflow):
    assert rule.rule_id == "test_rule"
    assert isinstance(rule._workflow_ref, ReferenceType)
    assert rule._workflow_ref() == workflow


def test_rule_repr_(rule):
    repr_str = rule.__repr__()
    assert "test_rule" in repr_str
    assert "test_method" in repr_str


def test_rule_to_dict(rule):
    rule_dict = rule.to_dict()
    assert rule_dict["method"] == "test_method"
    assert rule_dict["kwargs"] == {
        "input_file1": "test_file1",
        "input_file2": "test_file2",
        "param": "param",
    }
    assert rule_dict["rule_id"] == "test_rule"


def test_detect_wildcards(workflow):
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow, rule_id="test_rule")
    assert rule._wildcards == {"explode": ["region"], "expand": ["w"], "reduce": []}
    assert rule._wildcard_fields == {
        "region": ["input_file", "output_file", "output_file2", "root"],
        "w": ["output_file", "output_file2"],
    }

    reduce_method = MockReduceMethod(
        files=["test1_{w}", "test_2{w}"],
        root="/",
    )
    rule = Rule(method=reduce_method, workflow=workflow, rule_id="rule_id")
    assert rule._wildcards == {"explode": [], "expand": [], "reduce": ["w"]}
    assert rule._wildcard_fields == {"w": ["files"]}

    test_method = TestMethod(
        input_file1="{region}/test_file1", input_file2="{region}/test_file2"
    )
    rule = Rule(method=test_method, workflow=workflow, rule_id="test_method")
    assert rule._wildcards == {"explode": ["region"], "expand": [], "reduce": []}
    assert rule._wildcard_fields == {
        "region": ["input_file1", "input_file2", "output_file1", "output_file2"]
    }

    test_method = TestMethod(input_file1="testfile1", input_file2="testfile2")
    rule = Rule(method=test_method, workflow=workflow)
    assert rule._wildcards == {"explode": [], "expand": [], "reduce": []}


def test_validate_wildcards(workflow, test_method):
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow, rule_id="test_rule")
    rule.method = test_method
    err_msg = f"wildcard(s) {rule.wildcards['expand']} missing on inputs {test_method.dict['input']} for {test_method.name}"
    with pytest.raises(
        ValueError,
        match=re.escape(
            err_msg,
        ),
    ):
        rule._validate_wildcards()
    expand_method = MockExpandMethod(
        input_file="test_file", root="", events=["1", "2", "3"], wildcard="w"
    )
    expand_method.output = ExpandMethodOutput(output_file="test", output_file2="test2")
    err_msg = f"wildcard(s) missing on outputs {expand_method.dict['output']} for {expand_method.name}"
    with pytest.raises(
        ValueError,
        match=re.escape(err_msg),
    ):
        rule = Rule(method=expand_method, workflow=workflow, rule_id="test_rule")

    rule = Rule(method=test_method, workflow=workflow)
    rule.wildcards["reduce"] = "mock"
    err_msg = f"wildcard(s) mock missing on outputs {test_method.dict['output']} for {test_method.name}"
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        rule._validate_wildcards()

    reduce_method = MockReduceMethod(files="test1", root="")
    err_msg = f"wildcard(s) missing on inputs {reduce_method.dict['input']} for {reduce_method.name}"
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=reduce_method, workflow=workflow)


def test_method_wildcard_instance(rule, test_method, workflow):
    method = rule.method_wildcard_instance(wildcards={})
    assert method == test_method

    reduce_method = MockReduceMethod(files="test{region}", root="")

    rule = Rule(method=reduce_method, workflow=workflow)
    method = rule.method_wildcard_instance(wildcards={"region": ["1", "2"]})
    assert method.input.files == ["test1", "test2"]

    expand_method = MockExpandMethod(
        input_file="test_file",
        root="",
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    method = rule.method_wildcard_instance(wildcards={"w": [1, 2, 3]})
    assert method.output.output_file == PosixPath("{w}/file.yml")


def test_wildcard_product(workflow):
    test_method = TestMethod(input_file1="{region}/test1", input_file2="{region}/test2")

    rule = Rule(method=test_method, workflow=workflow)
    wc_product = rule.wildcard_product()

    assert isinstance(wc_product, list)
    assert wc_product[0]["region"] == workflow.wildcards.wildcards["region"][0]
    assert wc_product[1]["region"] == workflow.wildcards.wildcards["region"][1]

    reduce_method = MockReduceMethod(files="test{region}", root="")
    rule = Rule(method=reduce_method, workflow=workflow)
    wc_product = rule.wildcard_product()
    assert wc_product[0]["region"] == ["region1", "region2"]


def test_run(workflow, capsys, mocker):
    test_method = TestMethod(input_file1="{region}/test1", input_file2="{region}/test2")
    rule = Rule(method=test_method, workflow=workflow)
    mocker.patch.object(Rule, "_run_method_instance")
    rule.run(dryrun=True)
    captured = capsys.readouterr()
    assert "Run 1/2: {'region': 'region1'}" in captured.out
    assert "Run 2/2: {'region': 'region2'}" in captured.out

    mock_thread_map = mocker.patch("hydroflows.workflow.rule.thread_map")
    rule.run(max_workers=2)
    mock_thread_map.assert_called_with(
        rule._run_method_instance, rule.wildcard_product(), max_workers=2
    )
    rule.run(dryrun=True)
    captured = capsys.readouterr()
    assert "Run 1/2: {'region': 'region1'}" in captured.out
    assert "Run 2/2: {'region': 'region2'}" in captured.out


def test_run_method_instance(workflow, mocker):
    test_method = TestMethod(input_file1="{region}/test1", input_file2="{region}/test2")
    rule = Rule(method=test_method, workflow=workflow)

    mocker.patch.object(TestMethod, "dryrun")
    rule._run_method_instance(
        wildcards={"region": ["region1", "region1"]},
        dryrun=True,
        missing_file_error=True,
    )
    test_method.dryrun.assert_called_with(missing_file_error=True)
    mocker.patch.object(TestMethod, "run_with_checks")
    rule._run_method_instance(wildcards={"region": ["region1", "region1"]})
    test_method.run_with_checks.assert_called()


def test_rules(workflow, rule):
    reduce_method = MockReduceMethod(files="test{region}", root="")
    reduce_rule = Rule(method=reduce_method, workflow=workflow, rule_id="reduce_rule")
    rules = Rules(rules=[rule, reduce_rule])
    assert rules.names == ["test_rule", "reduce_rule"]
    assert (
        rules.__repr__()
        == "[Rule(id=test_rule, method=test_method, runs=1)\nRule(id=reduce_rule, method=mock_reduce_method, runs=1, reduce=['region'])]"
    )
    assert rule == rules.get_rule(rule_id="test_rule")

    with pytest.raises(ValueError, match="Rule fake_rule not found."):
        rules.get_rule(rule_id="fake_rule")

    class mock_rule:
        rule_id = "mock_rule"

    with pytest.raises(ValueError, match="Rule should be an instance of Rule."):
        rules.set_rule(mock_rule())

    with pytest.raises(ValueError, match="Rule test_rule already exists"):
        rules.set_rule(rule)
