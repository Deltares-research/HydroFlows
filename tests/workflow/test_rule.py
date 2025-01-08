import logging
import re
from itertools import chain
from weakref import ReferenceType

import pytest

from hydroflows.workflow import Rule
from hydroflows.workflow.rule import Rules
from hydroflows.workflow.workflow import Workflow
from tests.workflow.conftest import (
    ExpandMethodOutput,
    MockExpandMethod,
    MockReduceMethod,
    TestMethod,
)


def test_rule_init(rule: Rule, workflow: Workflow):
    assert rule.rule_id == "test_rule"
    assert isinstance(rule._workflow_ref, ReferenceType)
    assert rule._workflow_ref() == workflow


def test_rule_repr_(rule: Rule):
    repr_str = rule.__repr__()
    assert "test_rule" in repr_str
    assert "test_method" in repr_str


def test_rule_to_dict(rule: Rule):
    rule_dict = rule.to_dict()
    assert rule_dict["method"] == "test_method"
    assert rule_dict["kwargs"] == {
        "input_file1": "$config.test_rule_input_file1",
        "input_file2": "$config.test_rule_input_file2",
        "out_root": "$config.test_rule_out_root",
        "param": "$config.test_rule_param",
    }
    assert rule_dict["rule_id"] == "test_rule"


def test_detect_wildcards_explode_expand(workflow: Workflow):
    # test expand method with explode and expand wildcards
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


def test_detect_wildcards_reduce(workflow: Workflow):
    # test reduce method with reduce wildcards
    reduce_method = MockReduceMethod(
        files="test_{region}",
        root="/",
    )
    rule = Rule(method=reduce_method, workflow=workflow, rule_id="rule_id")
    assert rule._wildcards == {"explode": [], "expand": [], "reduce": ["region"]}
    assert rule._wildcard_fields == {"region": ["files"]}


def test_detect_wildcards_explode(workflow: Workflow):
    # test normal method with explode wildcards
    test_method = TestMethod(
        input_file1="{region}/test_file1", input_file2="{region}/test_file2"
    )
    rule = Rule(method=test_method, workflow=workflow, rule_id="test_method")
    assert rule._wildcards == {"explode": ["region"], "expand": [], "reduce": []}
    assert rule._wildcard_fields == {
        "region": [
            "input_file1",
            "input_file2",
            "output_file1",
            "output_file2",
            "out_root",
        ]
    }


def test_detect_wildcards_none(workflow: Workflow):
    # test normal method with no wildcards
    test_method = TestMethod(input_file1="testfile1", input_file2="testfile2")
    rule = Rule(method=test_method, workflow=workflow)
    assert rule._wildcards == {"explode": [], "expand": [], "reduce": []}


def test_detect_wildcards_params_explode(workflow: Workflow):
    # test normal method with expand wildcards on a param field
    test_method = TestMethod(
        input_file1="testfile1", input_file2="testfile2", out_root="{region}"
    )
    rule = Rule(method=test_method, workflow=workflow)
    assert rule._wildcards == {"explode": ["region"], "expand": [], "reduce": []}
    assert rule._wildcard_fields == {
        "region": ["output_file1", "output_file2", "out_root"]
    }


def test_detect_wildcards_params_explode_expand(workflow: Workflow):
    # test expand method with explode on a param field
    expand_method = MockExpandMethod(
        input_file="test_file",
        root="{region}",  # param field
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow, rule_id="test_rule")
    assert rule._wildcards == {"explode": ["region"], "expand": ["w"], "reduce": []}


def test_validate_wildcards(workflow: Workflow):
    # test expand method with missing wildcard on output
    name = MockExpandMethod.name
    expand_method = MockExpandMethod(
        input_file="test_file", root="", events=["1", "2", "3"], wildcard="w"
    )
    expand_method.output = ExpandMethodOutput(
        output_file="test", output_file2="test2"
    )  # replace output
    err_msg = f"ExpandMethod {name} requires a new expand wildcard on output (Rule test_rule)."
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=expand_method, workflow=workflow, rule_id="test_rule")

    # test with wrong wildcard on input
    expand_method = MockExpandMethod(
        input_file="{w}_test_file", root="", events=["1", "2", "3"], wildcard="w"
    )
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=expand_method, workflow=workflow, rule_id="test_rule")

    # test reduce method with missing wildcard on input
    name = MockReduceMethod.name
    reduce_method = MockReduceMethod(files=["test1"], root="")
    err_msg = (
        f"ReduceMethod {name} requires a reduce wildcard on input only (Rule {name})."
    )
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=reduce_method, workflow=workflow)

    # test with wrong wildcard on output
    reduce_method = MockReduceMethod(files="test{w}", root="{w}")
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=reduce_method, workflow=workflow)

    # test normal method with missing wildcard on output
    name = TestMethod.name
    test_method = TestMethod(
        input_file1="{region}/test1", input_file2="{region}/test2", out_root=""
    )
    err_msg = f"Wildcard(s) ['region'] missing on output or method {name} should be a ReduceMethod (Rule {name})."
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=test_method, workflow=workflow)

    # test normal method with missing wildcard on input
    test_method = TestMethod(input_file1="test1", input_file2="test2")
    test_method.output = test_method.output.model_copy(
        update=dict(output_file1="{region}/test1")
    )
    err_msg = f"Wildcard(s) ['region'] missing on input or method {name} should be an ExpandMethod (Rule {name})."
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=test_method, workflow=workflow)


def test_method_wildcard_instance(workflow: Workflow):
    # test normal method with no wildcards
    test_method = TestMethod(input_file1="test1", input_file2="test2")
    rule = Rule(method=test_method, workflow=workflow)
    method = rule._method_wildcard_instance(wildcards={})
    assert method == test_method

    # test normal method with explode wildcards
    explode_method = TestMethod(
        input_file1="{region}/test1", input_file2="{region}/test2"
    )
    rule = Rule(method=explode_method, workflow=workflow)
    method = rule._method_wildcard_instance(wildcards={"region": "region1"})
    assert method.input.input_file1.as_posix() == "region1/test1"
    method = rule._method_wildcard_instance(wildcards={"region": "xxx"})
    assert method.input.input_file1.as_posix() == "xxx/test1"
    with pytest.raises(
        ValueError, match="Explode wildcard 'region' should be a string."
    ):
        rule._method_wildcard_instance(wildcards={"region": ["1"]})

    # test reduce method
    reduce_method = MockReduceMethod(files="test{region}", root="")
    rule = Rule(method=reduce_method, workflow=workflow)
    method = rule._method_wildcard_instance(wildcards={"region": ["1", "2"]})
    assert [file.as_posix() for file in method.input.files] == ["test1", "test2"]
    with pytest.raises(ValueError, match="Reduce wildcard 'region' should be a list."):
        rule._method_wildcard_instance(wildcards={"region": "1"})

    # test expand method (creates 'w' wildcard on outputs)
    expand_method = MockExpandMethod(
        input_file="test_file",
        root="",
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    method: MockExpandMethod = rule._method_wildcard_instance(wildcards={})
    assert [file.as_posix() for file in method.output.output_file] == [
        "1/file.yml",
        "2/file.yml",
        "3/file.yml",
    ]
    with pytest.raises(
        ValueError, match="Expand wildcard 'w' should not be in wildcards."
    ):
        rule._method_wildcard_instance(wildcards={"w": [1, 2, 3]})

    # test expand method with additional explode wildcard
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2", "3"],
        wildcard="event",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    method: MockExpandMethod = rule._method_wildcard_instance(
        wildcards={"region": "region1"}
    )
    assert method.input.input_file.as_posix() == "region1/test_file"
    # assert method.output.output_file.as_posix() == "region1/{event}/file.yml"
    assert [file.as_posix() for file in method.output.output_file] == [
        "region1/1/file.yml",
        "region1/2/file.yml",
        "region1/3/file.yml",
    ]


def test_wildcard_product():
    # test normal method with explode (in- and output) wildcards
    workflow = Workflow(wildcards={"region": ["region1", "xx"]})
    test_method = TestMethod(input_file1="{region}/test1", input_file2="{region}/test2")
    rule = Rule(method=test_method, workflow=workflow)
    wc_product = rule.wildcard_product()
    assert wc_product == [{"region": "region1"}, {"region": "xx"}]

    # test reduce method
    reduce_method = MockReduceMethod(files="test{region}", root="")
    rule = Rule(method=reduce_method, workflow=workflow)
    wc_product = rule.wildcard_product()
    assert wc_product == [{"region": ["region1", "xx"]}]

    # test expand method with explode and expand wildcards
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2", "3"],
        wildcard="event",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    assert workflow.wildcards.get("event") == ["1", "2", "3"]
    wc_product = rule.wildcard_product()
    assert wc_product == [{"region": "region1"}, {"region": "xx"}]

    # test reduce method with expand wildcards
    workflow = Workflow(wildcards={"region": ["region1", "xx"], "event": ["1", "b"]})
    reduce_method = MockReduceMethod(files="{region}/test{event}", root="{region}")
    rule = Rule(method=reduce_method, workflow=workflow)
    wc_product = rule.wildcard_product()
    assert wc_product == [
        {"region": "region1", "event": ["1", "b"]},
        {"region": "xx", "event": ["1", "b"]},
    ]


def test_create_references_for_method_inputs(workflow: Workflow):
    method1 = TestMethod(input_file1="test.file", input_file2="test2.file")
    workflow.add_rule(method=method1, rule_id="method1")
    method2 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=workflow.get_ref("$rules.method1.output.output_file2"),
        out_root="root",
    )
    workflow.add_rule(method=method2, rule_id="method2")
    # Assert that refs of inputs of first rule are pointing to config
    assert workflow.rules[0].method.input._refs == {
        "input_file1": "$config.method1_input_file1",
        "input_file2": "$config.method1_input_file2",
    }
    # Assert that workflow config contains the input values of the first rule
    assert workflow.config.method1_input_file1 == "test.file"
    assert workflow.config.method1_input_file2 == "test2.file"
    # Assert that refs of second rule point to output of first rule
    assert workflow.rules[1].method.input._refs == {
        "input_file1": "$rules.method1.output.output_file1",
        "input_file2": "$rules.method1.output.output_file2",
    }


def test_add_method_params_to_config(workflow: Workflow):
    method = TestMethod(
        input_file1="test.file", input_file2="test2.file", param="test_param"
    )
    workflow.add_rule(method=method)
    # Assert the non-default test_param has been moved to config
    assert workflow.config.test_method_param == "test_param"
    assert workflow.rules[0].method.params._refs == {
        "param": "$config.test_method_param",
        "out_root": "$config.test_method_out_root",
    }
    # default_param should not be included in workflow.config
    assert "default_param" not in workflow.config.to_dict().values()
    assert "default_param2" not in workflow.config.to_dict().values()


def test_rule_dependency(workflow: Workflow):
    # Test for rule with no dependencies
    method1 = TestMethod(input_file1="file1", input_file2="file2")
    workflow.add_rule(method=method1, rule_id="method1")
    assert workflow.rules["method1"]._dependency is None

    # Test for rule with single dependency
    method2 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=workflow.get_ref("$rules.method1.output.output_file2"),
        out_root="root",
    )
    workflow.add_rule(method=method2, rule_id="method2")
    assert workflow.rules["method2"]._dependency == "method1"

    # Test for rule with multiple different dependencies
    method3 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=method2.output.output_file2,
        out_root="root3",
    )
    workflow.add_rule(method=method3, rule_id="method3")
    assert workflow.rules["method3"]._dependency == "method2"

    # Test for rule with single dependency not being the last in workflow.rules
    method4 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=method1.output.output_file2,
        out_root="root4",
    )
    workflow.add_rule(method=method4, rule_id="method4")
    assert workflow.rules["method4"]._dependency == "method1"


def test_parameters(workflow: Workflow):
    # Test for rule with no wildcard
    test_method = TestMethod(input_file1="test1", input_file2="test2")
    rule = Rule(method=test_method, workflow=workflow)
    assert rule._parameters == {
        "input": {
            "input_file1": [rule.method.input.input_file1],
            "input_file2": [rule.method.input.input_file2],
        },
        "output": {
            "output_file1": [rule.method.output.output_file1],
            "output_file2": [rule.method.output.output_file2],
        },
        "params": {
            "param": [rule.method.params.param],
            "out_root": [rule.method.input.input_file1.parent],
            "default_param": [rule.method.params.default_param],
            "default_param2": [rule.method.params.default_param2],
        },
    }

    # Test for rule with explode wildcard
    explode_method = TestMethod(
        input_file1="{region}/test1", input_file2="{region}/test2"
    )
    rule = Rule(method=explode_method, workflow=workflow)
    methods = rule._method_instances
    assert rule._parameters == {
        "input": {
            "input_file1": [method.input.input_file1 for method in methods],
            "input_file2": [method.input.input_file2 for method in methods],
        },
        "output": {
            "output_file1": [method.output.output_file1 for method in methods],
            "output_file2": [method.output.output_file2 for method in methods],
        },
        "params": {
            "param": [methods[0].params.param],
            "out_root": [
                method.params.out_root for method in methods
            ],  # has region wildcard
            "default_param": [methods[0].params.default_param],
            "default_param2": [methods[0].params.default_param2],
        },
    }

    # Test for reduce rule
    reduce_method = MockReduceMethod(files="test{region}", root="")
    rule = Rule(method=reduce_method, workflow=workflow)
    # only 1 instance for reduce rules
    methods = rule._method_instances
    assert rule._parameters == {
        "input": {
            # Evaluated input is already a list, so no extra brackets
            "files": methods[0].input.files
        },
        "output": {"output_file": [methods[0].output.output_file]},
        "params": {"root": [methods[0].params.root]},
    }

    # Test for expand rule
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2"],
        wildcard="event",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    methods = rule._method_instances
    assert rule._parameters == {
        "input": {"input_file": [method.input.input_file for method in methods]},
        "output": {
            # _parameters flattens nested list
            "output_file": list(
                chain(*[method.output.output_file for method in methods])
            ),
            "output_file2": list(
                chain(*[method.output.output_file2 for method in methods])
            ),
        },
        "params": {
            "root": [method.params.root for method in methods],
            "events": [methods[0].params.events],
            "wildcard": [methods[0].params.wildcard],
        },
    }


def test_run(caplog, mocker):
    caplog.set_level(logging.INFO)
    workflow = Workflow(wildcards={"region": ["region1", "region2"]})
    test_method = TestMethod(input_file1="{region}/test1", input_file2="{region}/test2")
    rule = Rule(method=test_method, workflow=workflow)
    mocker.patch.object(Rule, "_run_method_instance")
    rule.run(dryrun=True)
    assert "Running test_method 1/2" in caplog.text
    assert "Running test_method 2/2" in caplog.text

    mock_thread_map = mocker.patch("hydroflows.workflow.rule.thread_map")
    rule.run(max_workers=2)
    mock_thread_map.assert_called_with(
        rule._run_method_instance, rule._method_instances, max_workers=2
    )
    rule.run(dryrun=True)
    assert "Running test_method 1/2" in caplog.text
    assert "Running test_method 2/2" in caplog.text


def test_run_method_instance(mocker):
    workflow = Workflow(wildcards={"region": ["region1", "region2"]})
    test_method = TestMethod(input_file1="test1", input_file2="test2")
    rule = Rule(method=test_method, workflow=workflow)

    mocker.patch.object(TestMethod, "dryrun")
    rule._run_method_instance(
        method=rule._method_instances[0],
        dryrun=True,
        missing_file_error=True,
    )
    test_method.dryrun.assert_called_with(missing_file_error=True)
    mocker.patch.object(TestMethod, "run_with_checks")
    rule._run_method_instance(method=rule._method_instances[0])
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
