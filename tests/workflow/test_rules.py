import pytest
from conftest import MockReduceMethod, TestMethod

from hydroflows.workflow.rule import Rule
from hydroflows.workflow.rules import Rules
from hydroflows.workflow.workflow import Workflow


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


# FIXME see if we can do tests directly on Rules class instead of using Workflow


def test_rule_dependency(workflow: Workflow):
    # Test for rule with no dependencies
    method1 = TestMethod(input_file1="file1", input_file2="file2")
    workflow.create_rule(method=method1, rule_id="method1")
    assert workflow.rules.dependency_map.get("method1") == []

    # Test for rule with single dependency
    method2 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=workflow.get_ref("$rules.method1.output.output_file2"),
        out_root="root",
    )
    workflow.create_rule(method=method2, rule_id="method2")
    assert workflow.rules.dependency_map.get("method2") == ["method1"]

    # Test for rule with multiple different dependencies
    method3 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=method2.output.output_file2,
        out_root="root3",
    )
    workflow.create_rule(method=method3, rule_id="method3")
    assert workflow.rules.dependency_map.get("method3") == ["method1", "method2"]

    # Test for rule with single dependency not being the last in workflow.rules
    method4 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=method1.output.output_file2,
        out_root="root4",
    )
    workflow.create_rule(method=method4, rule_id="method4")
    assert workflow.rules.dependency_map.get("method4") == ["method1"]

    # test result_rules (rules that are not dependencies of any other rule)
    assert workflow.rules.result_rules == ["method3", "method4"]


def test_rules_order(workflow: Workflow):
    method1 = TestMethod(input_file1="file1", input_file2="file2")
    workflow.create_rule(method=method1, rule_id="method1")

    method2 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=workflow.get_ref("$rules.method1.output.output_file2"),
        out_root="root",
    )
    workflow.create_rule(method=method2, rule_id="method2")

    method3 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=method2.output.output_file2,
        out_root="root3",
    )
    workflow.create_rule(method=method3, rule_id="method3")

    method4 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=method1.output.output_file2,
        out_root="root4",
    )
    workflow.create_rule(method=method4, rule_id="method4")

    assert workflow.rules.names == ["method1", "method4", "method2", "method3"]
