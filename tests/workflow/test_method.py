from pprint import pformat

import pytest

from hydroflows.workflow import Method, Parameters


class TestMethod(Method):
    name: str = "test_method"

    def __init__(self) -> None:
        super().__init__()

    def run(self):
        pass


def test_method_param_props():
    test_method = TestMethod()
    delattr(test_method, "_input")
    with pytest.raises(ValueError, match="Input parameters not set"):
        test_method.input  # noqa
    delattr(test_method, "_output")
    with pytest.raises(ValueError, match="Output parameters not set"):
        test_method.output  # noqa
    delattr(test_method, "_params")
    assert isinstance(test_method.params, Parameters)

    test_method = TestMethod()
    with pytest.raises(ValueError, match="Input should be a Parameters instance"):
        test_method.input = "input param"
    with pytest.raises(ValueError, match="Output should be a Parameters instance"):
        test_method.output = "output param"
    with pytest.raises(ValueError, match="Params should be a Parameters instance"):
        test_method.params = "param"


def test_method_repr():
    test_method = TestMethod()
    assert test_method.name in test_method.__repr__()
    assert f"parameters={pformat(test_method.dict)}" in test_method.__repr__()


def test_method_kwargs():
    pass


def test_method_kwargs_with_refs():
    pass


def test_method_dict():
    pass


def test_method_to_dict():
    pass
