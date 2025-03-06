import logging
import re
from itertools import chain
from pathlib import Path
from weakref import ReferenceType

import pytest

from hydroflows.workflow import Rule
from hydroflows.workflow.method import Method
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
    assert rule.workflow == workflow


def test_rule_properties(rule: Rule):
    assert isinstance(rule.method, Method)
    assert rule.n_runs == 1
    assert rule.wildcards == {"repeat": [], "expand": [], "reduce": []}
    assert rule.wildcard_fields == {}
    assert len(rule._method_instances) == 1
    assert rule.input == {
        "input_file1": [Path("test_file1")],
        "input_file2": [Path("test_file2")],
    }
    assert rule.output == {
        "output_file1": [Path("output1")],
        "output_file2": [Path("output2")],
    }


def test_rule_properties_expand(workflow: Workflow):
    # test expand method with repeat and expand wildcards
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow, rule_id="test_rule")
    assert rule.wildcards == {"repeat": ["region"], "expand": ["w"], "reduce": []}
    assert rule.wildcard_fields == {
        "region": ["input_file", "output_file", "output_file2", "root"],
        "w": ["output_file", "output_file2"],
    }
    assert rule.n_runs == 2
    assert len(rule._method_instances) == 2


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


def test_detect_wildcards_reduce(workflow: Workflow):
    # test reduce method with reduce wildcards
    reduce_method = MockReduceMethod(
        files="test_{region}",
        root="/",
    )
    rule = Rule(method=reduce_method, workflow=workflow, rule_id="rule_id")
    assert rule._wildcards == {"repeat": [], "expand": [], "reduce": ["region"]}
    assert rule._wildcard_fields == {"region": ["files"]}


def test_detect_wildcards_repeat(workflow: Workflow):
    # test normal method with repeat wildcards
    test_method = TestMethod(
        input_file1="{region}/test_file1", input_file2="{region}/test_file2"
    )
    rule = Rule(method=test_method, workflow=workflow, rule_id="test_method")
    assert rule._wildcards == {"repeat": ["region"], "expand": [], "reduce": []}
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
    assert rule._wildcards == {"repeat": [], "expand": [], "reduce": []}


def test_detect_wildcards_params_repeat(workflow: Workflow):
    # test normal method with expand wildcards on a param field
    test_method = TestMethod(
        input_file1="testfile1", input_file2="testfile2", out_root="{region}"
    )
    rule = Rule(method=test_method, workflow=workflow)
    assert rule._wildcards == {"repeat": ["region"], "expand": [], "reduce": []}
    assert rule._wildcard_fields == {
        "region": ["output_file1", "output_file2", "out_root"]
    }


def test_detect_wildcards_params_repeat_expand(workflow: Workflow):
    # test expand method with repeat on a param field
    expand_method = MockExpandMethod(
        input_file="test_file",
        root="{region}",  # param field
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow, rule_id="test_rule")
    assert rule._wildcards == {"repeat": ["region"], "expand": ["w"], "reduce": []}


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
        Rule(method=expand_method, workflow=Workflow(), rule_id="test_rule")

    # test with wrong wildcard on input
    expand_method = MockExpandMethod(
        input_file="{w}_test_file", root="", events=["1", "2", "3"], wildcard="w"
    )
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Rule(method=expand_method, workflow=Workflow(), rule_id="test_rule")

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


def test_create_method_instance(workflow: Workflow):
    # test normal method with no wildcards
    test_method = TestMethod(input_file1="test1", input_file2="test2")
    rule = Rule(method=test_method, workflow=workflow)
    method = rule._create_method_instance(wildcards={})
    assert method == test_method

    # test normal method with repeat wildcards
    repeat_method = TestMethod(
        input_file1="{region}/test1", input_file2="{region}/test2"
    )
    rule = Rule(method=repeat_method, workflow=workflow)
    method = rule._create_method_instance(wildcards={"region": "region1"})
    assert method.input.input_file1.as_posix() == "region1/test1"
    method = rule._create_method_instance(wildcards={"region": "xxx"})
    assert method.input.input_file1.as_posix() == "xxx/test1"
    with pytest.raises(
        ValueError, match="Repeat wildcard 'region' should be a string."
    ):
        rule._create_method_instance(wildcards={"region": ["1"]})

    # test reduce method
    reduce_method = MockReduceMethod(files="test{region}", root="")
    rule = Rule(method=reduce_method, workflow=workflow)
    method = rule._create_method_instance(wildcards={"region": ["1", "2"]})
    assert [file.as_posix() for file in method.input.files] == ["test1", "test2"]
    with pytest.raises(ValueError, match="Reduce wildcard 'region' should be a list."):
        rule._create_method_instance(wildcards={"region": "1"})

    # test expand method (creates 'w' wildcard on outputs)
    expand_method = MockExpandMethod(
        input_file="test_file",
        root="",
        events=["1", "2", "3"],
        wildcard="w",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    method: MockExpandMethod = rule._create_method_instance(wildcards={})
    assert method.output.output_file.as_posix() == "{w}/file.yml"
    with pytest.raises(
        ValueError, match="Expand wildcard 'w' should not be in wildcards."
    ):
        rule._create_method_instance(wildcards={"w": [1, 2, 3]})

    # test expand method with additional repeat wildcard
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2", "3"],
        wildcard="event",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    method: MockExpandMethod = rule._create_method_instance(
        wildcards={"region": "region1"}
    )
    assert method.input.input_file.as_posix() == "region1/test_file"
    assert method.output.output_file.as_posix() == "region1/{event}/file.yml"


def test_wildcard_product():
    # test normal method with repeat (in- and output) wildcards
    workflow = Workflow(wildcards={"region": ["region1", "xx"]})
    test_method = TestMethod(input_file1="{region}/test1", input_file2="{region}/test2")
    rule = Rule(method=test_method, workflow=workflow)
    wc_product = rule._wildcard_product
    assert wc_product == [{"region": "region1"}, {"region": "xx"}]

    # test reduce method
    reduce_method = MockReduceMethod(files="test{region}", root="")
    rule = Rule(method=reduce_method, workflow=workflow)
    wc_product = rule._wildcard_product
    assert wc_product == [{"region": ["region1", "xx"]}]

    # test expand method with repeat and expand wildcards
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2", "3"],
        wildcard="event",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    assert workflow.wildcards.get("event") == ["1", "2", "3"]
    wc_product = rule._wildcard_product
    assert wc_product == [{"region": "region1"}, {"region": "xx"}]

    # test reduce method with expand wildcards
    workflow = Workflow(wildcards={"region": ["region1", "xx"], "event": ["1", "b"]})
    reduce_method = MockReduceMethod(files="{region}/test{event}", root="{region}")
    rule = Rule(method=reduce_method, workflow=workflow)
    wc_product = rule._wildcard_product
    assert wc_product == [
        {"region": "region1", "event": ["1", "b"]},
        {"region": "xx", "event": ["1", "b"]},
    ]


def test_create_references_for_method_inputs(workflow: Workflow):
    method1 = TestMethod(input_file1="test.file", input_file2="test2.file")
    workflow.create_rule(method=method1, rule_id="method1")
    method2 = TestMethod(
        input_file1=method1.output.output_file1,
        input_file2=workflow.get_ref("$rules.method1.output.output_file2"),
        out_root="root",
    )
    workflow.create_rule(method=method2, rule_id="method2")
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

    method3 = TestMethod(
        input_file1="test.file",
        input_file2=workflow.get_ref("$rules.method2.output.output_file2"),
        out_root="new_root",
    )
    workflow.create_rule(method3, rule_id="method3")
    assert workflow.rules[2].method.input._refs == {
        "input_file1": "$config.method1_input_file1",
        "input_file2": "$rules.method2.output.output_file2",
    }


def test_add_method_params_to_config(workflow: Workflow):
    method = TestMethod(
        input_file1="test.file", input_file2="test2.file", param="test_param"
    )
    workflow.create_rule(method=method)
    # Assert the non-default test_param has been moved to config
    assert workflow.config.test_method_param == "test_param"
    assert workflow.rules[0].method.params._refs == {
        "param": "$config.test_method_param",
        "out_root": "$config.test_method_out_root",
    }
    # default_param should not be included in workflow.config
    assert "default_param" not in workflow.config.to_dict().values()
    assert "default_param2" not in workflow.config.to_dict().values()

    # Check whether ref to value already in config is correctly set
    method2 = TestMethod(
        input_file1="test.file",
        input_file2="test2.file",
        out_root="root",
        param="test_param",
    )
    workflow.create_rule(method2, rule_id="method2")
    assert workflow.rules[1].method.params._refs == {
        "param": "$config.test_method_param",
        "out_root": "$config.method2_out_root",
    }
    # make sure not a new param is added to config
    assert "method2_param" not in workflow.config.to_dict().keys()

    # Make sure not a new item is added to config if param is already a ref
    method3 = TestMethod(
        input_file1="test.file",
        input_file2="test2.file",
        out_root="root3",
        param=workflow.get_ref("$config.test_method_param"),
    )
    workflow.create_rule(method3, rule_id="method3")
    assert "method3_param" not in workflow.config.to_dict().keys()

    # Make sure param is not added to config if it contains a wildcard
    method4 = TestMethod(
        input_file1="test.file",
        input_file2="test2.file",
        param="{region}",
        out_root="{region}",
    )
    workflow.create_rule(method4, rule_id="method4")
    assert "method4_param" not in workflow.config.to_dict().keys()


def test_input_output(workflow: Workflow):
    # Test for rule with no wildcard
    test_method = TestMethod(input_file1="test1", input_file2="test2")
    rule = Rule(method=test_method, workflow=workflow)
    assert rule._input == {
        "input_file1": [test_method.input.input_file1],
        "input_file2": [test_method.input.input_file2],
    }
    assert rule._output == {
        "output_file1": [test_method.output.output_file1],
        "output_file2": [test_method.output.output_file2],
    }

    # Test for rule with repeat wildcard
    repeat_method = TestMethod(
        input_file1="{region}/test1", input_file2="{region}/test2"
    )
    rule = Rule(method=repeat_method, workflow=workflow)
    methods: list[TestMethod] = rule._method_instances
    assert rule._input == {
        "input_file1": [method.input.input_file1 for method in methods],
        "input_file2": [method.input.input_file2 for method in methods],
    }
    assert rule._output == {
        "output_file1": [method.output.output_file1 for method in methods],
        "output_file2": [method.output.output_file2 for method in methods],
    }

    # Test for reduce rule
    reduce_method = MockReduceMethod(files="test{region}", root="")
    rule = Rule(method=reduce_method, workflow=workflow)
    # only 1 instance for reduce rules
    methods: list[MockReduceMethod] = rule._method_instances
    assert rule._input == {
        # Evaluated input is already a list, so no extra brackets
        "files": methods[0].input.files
    }
    assert rule._output == {
        "output_file": [methods[0].output.output_file],
    }

    # Test for expand rule
    expand_method = MockExpandMethod(
        input_file="{region}/test_file",
        root="{region}",
        events=["1", "2"],
        wildcard="event",
    )
    rule = Rule(method=expand_method, workflow=workflow)
    methods: list[MockExpandMethod] = rule._method_instances
    assert rule._input == {
        "input_file": [method.input.input_file for method in methods]
    }
    assert rule._output == {
        # flattens nested list
        "output_file": list(
            chain(*[method.output_expanded["output_file"] for method in methods])
        ),
        "output_file2": list(
            chain(*[method.output_expanded["output_file2"] for method in methods])
        ),
    }


def test_dryrun(caplog, tmp_path):
    caplog.set_level(logging.INFO)
    workflow = Workflow(wildcards={"region": ["region1", "region2"]}, root=tmp_path)
    test_method = TestMethod(input_file1="{region}/test1", input_file2="{region}/test2")
    rule = Rule(method=test_method, workflow=workflow)
    # test dryrun without missing file error
    rule.dryrun(missing_file_error=False)
    assert "Running test_method 1/2" in caplog.text
    assert "Running test_method 2/2" in caplog.text
    # test dryrun with missing file error
    with pytest.raises(FileNotFoundError):
        rule.dryrun(missing_file_error=True)
    # test dryrun with missing file error and missing file
    input_files = []
    for file_list in rule._input.values():
        input_files.extend(file_list)
    rule.dryrun(missing_file_error=True, input_files=input_files)
    # write input files and test again
    for file in input_files:
        abs_path = Path(workflow.root, file)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text("")
    rule.dryrun(missing_file_error=True)


def test_run(caplog, mocker):
    caplog.set_level(logging.INFO)
    workflow = Workflow(wildcards={"region": ["region1", "region2"]})
    test_method = TestMethod(input_file1="{region}/test1", input_file2="{region}/test2")
    rule = Rule(method=test_method, workflow=workflow)
    # mock all run methods of methods in rule.methods
    mocker.patch.object(TestMethod, "run")
    rule.run()
    assert "Running test_method 1/2" in caplog.text
    assert "Running test_method 2/2" in caplog.text
    assert TestMethod.run.call_count == 2
    # test with max_workers
    rule.run(max_workers=2)
    assert TestMethod.run.call_count == 4


def test_output_path_refs(w: Workflow):
    method1 = TestMethod(input_file1="test1", input_file2="test2")
    w.create_rule(method=method1, rule_id="method1")

    output_path_refs = w.rules["method1"]._output_path_refs
    assert list(output_path_refs.keys()) == ["output" + str(x) for x in range(1, 3)]
