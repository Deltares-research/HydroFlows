import re

import pytest

from hydroflows.workflow import Ref, WorkflowConfig
from tests.workflow.conftest import MockExpandMethod


def test_ref_init(workflow):
    ref = Ref(ref="$config.rps", workflow=workflow)
    assert ref.value == [2, 50, 100]
    assert ref.workflow == workflow
    assert ref.ref == "$config.rps"


def test_ref_setter(workflow):
    ref = Ref(ref="$config.rps", workflow=workflow)
    with pytest.raises(ValueError, match="Reference should be a string."):
        ref.ref = 0
    err_msg = (
        "Invalid rule reference: $rules.rule_id.component. "
        "A rule reference should be in the form rules.<rule_id>.<component>.<key>, "
        "where <component> is one of input, output or params."
    )
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        ref.ref = "$rules.rule_id.component"

    err_msg = (
        "Invalid config reference: $config. "
        "A config reference should be in the form config.<key>."
    )
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        ref.ref = "$config"

    err_msg = (
        "Invalid wildcard reference: $wildcards. "
        "A wildcard reference should be in the form wildcards.<key>."
    )
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        ref.ref = "$wildcards"

    err_msg = "Reference should start with '$rules', '$config', or '$wildcards'."
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        ref.ref = "$fake_ref"


def test_ref_value_setter(workflow):
    workflow.config.rps = None
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Value should not be None. Reference $config.rps possibly not resolved."
        ),
    ):
        Ref(ref="$config.rps", workflow=workflow)


def test_ref_is_expand_method(workflow):
    ref = Ref("$config.rps", workflow=workflow)
    assert not ref.is_expand_field

    expand_method = MockExpandMethod(
        input_file="test_file",
        root="",
        events=["1", "2", "3"],
        wildcard="w",
    )
    workflow.add_rule(method=expand_method, rule_id="test_rule")
    ref = Ref("$rules.test_rule.input.input_file", workflow)
    assert not ref.is_expand_field

    ref = Ref("$rules.test_rule.output.output_file", workflow=workflow)
    assert ref.is_expand_field


def test_get_str_value(workflow):
    ref = Ref("$config.rps", workflow=workflow)
    assert ref.get_str_value() == "[2, 50, 100]"
    expand_method = MockExpandMethod(
        input_file="test_file",
        root="",
        events=["1", "2", "3"],
        wildcard="w",
    )
    workflow.add_rule(method=expand_method, rule_id="test_rule")
    ref = Ref("$rules.test_rule.output.output_file", workflow=workflow)
    assert ref.get_str_value(quote_str=False) == "{w}/file.yml"


def test_set_resolve_ref(workflow, mocker):
    ref = Ref("$config.rps", workflow=workflow)
    mock_set_resolve_rule_ref = mocker.patch.object(Ref, "_set_resolve_rule_ref")
    ref._set_resolve_ref("$rules")
    mock_set_resolve_rule_ref.assert_called_once_with("$rules")
    mock_set_resolve_config_ref = mocker.patch.object(Ref, "_set_resolve_config_ref")
    ref._set_resolve_ref("$config")
    mock_set_resolve_config_ref.assert_called_once_with("$config")
    mock_set_resolve_wildcard_ref = mocker.patch.object(
        Ref, "_set_resolve_wildcard_ref"
    )
    ref._set_resolve_ref("$wildcards")
    mock_set_resolve_wildcard_ref.assert_called_once_with("$wildcards")
    mock_get_obj_from_caller_globals = mocker.patch.object(
        Ref, "_get_obj_from_caller_globals"
    )
    mock_get_obj_from_caller_globals.return_value = None
    with pytest.raises(ValueError, match=re.escape("Invalid reference: $workflow")):
        ref._set_resolve_ref("$workflow")

    expand_method = MockExpandMethod(
        input_file="test_file",
        root="",
        events=["1", "2", "3"],
        wildcard="w",
    )
    workflow.add_rule(method=expand_method, rule_id="test_rule")
    mock_get_obj_from_caller_globals.return_value = workflow
    ref._set_resolve_ref("$workflow.config.rps")
    mock_set_resolve_config_ref.assert_called_with("$config.rps")

    mock_get_obj_from_caller_globals.return_value = expand_method
    mock_resolve_method_obj_ref = mocker.patch.object(Ref, "_resolve_method_obj_ref")
    ref._set_resolve_ref("expand_method.output.output_file")
    mock_resolve_method_obj_ref.assert_called_once_with(
        "expand_method.output.output_file", expand_method
    )
    mock_get_obj_from_caller_globals.return_value = workflow.config
    mock_resolve_config_obj_ref = mocker.patch.object(Ref, "_resolve_config_obj_ref")
    ref._set_resolve_ref("config.rps")
    mock_resolve_config_obj_ref.assert_called_once_with("config.rps", workflow.config)


def test_set_resolve_rule_ref(workflow):
    expand_method = MockExpandMethod(
        input_file="test_file",
        root="",
        events=["1", "2", "3"],
        wildcard="w",
    )
    workflow.add_rule(method=expand_method, rule_id="test_rule")
    ref = "$rules.test_rule.output.output_file3"
    err_msg = (
        f"Invalid reference: {ref}. "
        "Field output_file3 not found in rule test_rule.output."
    )
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Ref(ref, workflow=workflow)

    ref = Ref("$rules.test_rule.output.output_file", workflow=workflow)
    assert ref.value.as_posix() == "{w}/file.yml"


def test_set_resolve_config_ref(workflow):
    workflow.config = WorkflowConfig(rps=[1, 2, 3], test=[4, 5, 6])
    ref = Ref("$config.rps", workflow=workflow)
    ref._set_resolve_config_ref(ref="$config.test")
    assert ref.value == [4, 5, 6]


def test_set_resolve_wildcard_ref(workflow):
    ref = Ref("$wildcards.region", workflow=workflow)
    assert ref.value == ["region1", "region2"]


def test_set_resolve_method_obj_ref(workflow, mocker, test_method):
    expand_method = MockExpandMethod(
        input_file="test_file",
        root="",
        events=["1", "2", "3"],
        wildcard="w",
    )
    workflow.add_rule(method=expand_method, rule_id="test_rule")

    ref = Ref("$config.rps", workflow=workflow)

    mock_set_resolve_rule_ref = mocker.patch.object(Ref, "_set_resolve_rule_ref")

    err_msg = (
        "Invalid method reference $expand_method.output_file. "
        "A method reference should be in the form <method>.<component>.<field>"
    )
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        ref._resolve_method_obj_ref(
            ref="$expand_method.output_file", method=expand_method
        )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Invalid method reference $test_method.output.outputfile. Method not added to the workflow"
        ),
    ):
        ref._resolve_method_obj_ref(
            ref="$test_method.output.outputfile", method=test_method
        )

    ref._resolve_method_obj_ref(
        ref="$expand_method.output.output_file", method=expand_method
    )
    mock_set_resolve_rule_ref.assert_called_once_with(
        "$rules.test_rule.output.output_file"
    )


def test_resolve_config_obj_ref(workflow, mocker):
    ref = Ref("$config.rps", workflow=workflow)
    config = WorkflowConfig(test=1)
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Invalid config reference $config.test. Config not added to the workflow"
        ),
    ):
        ref._resolve_config_obj_ref(ref="$config.test", config=config)
    mock_set_resolve_config_ref = mocker.patch.object(Ref, "_set_resolve_config_ref")
    ref._resolve_config_obj_ref(ref="$config.rps", config=workflow.config)
    mock_set_resolve_config_ref.assert_called_with("$config.rps")


def test_get_nested_value_from_dict(workflow):
    full_reference = "$config.rps.rp"
    d = {"rps": {"rp": [1, 2, 3]}}
    keys = ["rps", "rp"]

    value = Ref._get_nested_value_from_dict(
        d=d, keys=keys, full_reference=full_reference
    )
    assert value == d["rps"]["rp"]

    with pytest.raises(KeyError, match=re.escape("Key not found: rps.pr")):
        Ref._get_nested_value_from_dict(d=d, keys=["rps", "pr"], full_reference=None)


TEST_VAR = "test_var"


def test_get_obj_from_caller_globals(workflow, test_method):
    foo = "bar"
    obj = Ref._get_obj_from_caller_globals(var_name="foo", ref="foo")
    assert obj == foo

    obj = Ref._get_obj_from_caller_globals(var_name="TEST_VAR", ref="TEST_VAR")
    assert obj == TEST_VAR
