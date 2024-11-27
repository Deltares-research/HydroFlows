import pytest

from hydroflows.methods import METHODS
from hydroflows.workflow import Method

ALL_METHODS = list(METHODS.entry_points.keys())


def _init_method(method: str) -> Method:
    # instantiate method with made-up kwargs
    method_class = METHODS.load(method)
    assert method_class.name.lower() == method.lower()
    kwargs = getattr(method_class, "_test_kwargs", {})
    if not kwargs:
        pytest.skip(f"Skipping {method_class} because it has no _test_kwargs")
    method: Method = method_class(**kwargs)
    return method


@pytest.mark.parametrize("name", ALL_METHODS)
def test_method_unique_keys(name: str):
    """Check if the method input, output and params keys are unique."""
    _init_method(name)._test_unique_keys()


@pytest.mark.parametrize("name", ALL_METHODS)
def test_method_roundtrip(name: str) -> None:
    """Test if the method can be serialized and deserialized."""
    _init_method(name)._test_roundtrip()
