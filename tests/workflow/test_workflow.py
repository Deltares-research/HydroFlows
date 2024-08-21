import pytest


from hydroflows.workflow import Workflow, WorkflowConfig, Method, Rule


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


def test_workflow_rule_from_kwargs(w)