import pytest

# load subclasses to discover all methods
from hydroflows.methods import METHODS
from hydroflows.workflow import Method

ALL_METHODS = list(METHODS.entry_points.keys())


@pytest.mark.parametrize("method", ALL_METHODS)
def test_methods(method: str):
    """Generic method tests."""
    # instantiate method with made-up kwargs
    method_class = METHODS.load(method)
    assert method_class.name.lower() == method.lower()
    kwargs = getattr(method_class, "_test_kwargs", {})
    if not kwargs:
        pytest.skip(f"Skipping {method_class} because it has no _test_kwargs")
    method: Method = method_class(**kwargs)
    # Test if all input, output and params fields have unique names
    method._test_unique_keys()
    # Test if all method __init__ arguments are in input, output or params.
    method._test_method_kwargs()
    # Test if the method can be serialized and deserialized
    method._test_roundtrip()
