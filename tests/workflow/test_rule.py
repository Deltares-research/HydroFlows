import re
from weakref import ReferenceType

import pytest
from conftest import ExpandMethodOutput, MockExpandMethod, MockReduceMethod

from hydroflows.workflow import Rule


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
        first_file=["test1_{w}", "test_2{w}"],
        second_file=["test1_{w}", "test2_{w}"],
        root="/",
    )
    rule = Rule(method=reduce_method, workflow=workflow, rule_id="rule_id")
    assert rule._wildcards == {"explode": [], "expand": [], "reduce": ["w"]}
    assert rule._wildcard_fields == {"w": ["first_file", "second_file"]}


def test_validate_wildcards(workflow, test_method):
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow, rule_id="test_rule")
    rule.method = test_method
    with pytest.raises(
        ValueError,
        match=re.escape(
            f"wildcard(s) {rule.wildcards['expand']} missing on inputs {test_method.dict['input']}"
        ),
    ):
        rule._validate_wildcards()
    expand_method = MockExpandMethod(
        input_file="test_file", root="", events=["1", "2", "3"], wildcard="w"
    )
    expand_method.output = ExpandMethodOutput(output_file="test", output_file2="test2")
    with pytest.raises(
        ValueError,
        match=re.escape(
            f"wildcard(s) missing on outputs {expand_method.dict['output']}"
        ),
    ):
        rule = Rule(method=expand_method, workflow=workflow, rule_id="test_rule")

    rule = Rule(method=test_method, workflow=workflow)
    rule.wildcards["reduce"] = "mock"
    err_msg = f"wildcard(s) mock missing on outputs {test_method.dict['output']}"
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        rule._validate_wildcards()

    reduce_method = MockReduceMethod(first_file="test1", second_file="test2", root="")
    err_msg = f"wildcard(s) missing on inputs {reduce_method.dict['input']}"
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=reduce_method, workflow=workflow)
