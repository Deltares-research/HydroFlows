import pytest
from importlib_metadata import EntryPoint

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_entrypoints import MethodEPS


def test_method_eps():
    name = "run_dummy_event"
    cls_name = "RunDummyEvent"
    module = "hydroflows.methods.dummy.run_dummy_event"
    ep_str = f"{module}:{cls_name}"

    m = MethodEPS({name: ep_str})
    assert len(m.entry_points) == 1
    # get_ep by name or class name (case insensitive)
    assert isinstance(m.get_ep(name), EntryPoint)
    assert isinstance(m.get_ep(name.upper()), EntryPoint)
    assert isinstance(m.get_ep(cls_name.lower()), EntryPoint)
    # load method by name or class name
    assert issubclass(m.load(name), Method)
    assert issubclass(m.load(cls_name), Method)
    # set_ep with EntryPoint instance or str
    m.set_ep("test_ep", m.get_ep(name))
    m.set_ep("test_str", ep_str)
    assert len(m.entry_points) == 3
    # check set_ep with invalid ep
    with pytest.raises(ValueError, match="Invalid entry point 123"):
        m.set_ep("test_invalid", 123)
    # raise ValueError if method already exists
    with pytest.raises(ValueError, match="Duplicate entry point run_dummy_event"):
        m.set_ep(name, ep_str)
    # raise ValueError if method not found
    with pytest.raises(ValueError, match="Method not_a_method not found"):
        m.load("not_a_method")
