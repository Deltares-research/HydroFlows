import pytest
import yaml
import os

from hydroflows.workflow import Workflow, WorkflowConfig, Method, Rule, Ref


@pytest.fixture
def w():
    config = {"rps": [2, 50, 100]}
    wildcards = {"region": ["region1", "region2"]}
    return Workflow(name="wf_instance", config=config, wildcards=wildcards)


@pytest.fixture
def mock_method(mocker):
    mocker.patch.multiple(Method, __abstractmethods__=set())
    instance = Method()
    return instance


def test_workflow_init(w):
    assert isinstance(w.config, WorkflowConfig)
    assert isinstance(w.wildcards.wildcards, dict)
    assert w.config._workflow_name == "wf_instance"


def test_workflow_repr(w, mock_method):
    w.add_rule(method=mock_method, rule_id="mock_rule")
    repr_str = w.__repr__()
    assert "region1" in repr_str
    assert "region2" in repr_str
    assert "mock_rule" in repr_str


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


def test_workflow_from_yaml(tmpdir):
    yaml_fn = "examples/sfincs_pluvial.yml"
    w = Workflow.from_yaml(file=yaml_fn)
    assert isinstance(w, Workflow)
    assert w.rules[0].rule_id == "sfincs_build"

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


def test_workflow_to_snakemake():
    pass
