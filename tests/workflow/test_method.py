import pytest

from hydroflows.workflow.method import Method


@pytest.fixture()
def test_method():
    class TestMethod(Method):
        def __init__(self) -> None:
            super().__init__()

    return TestMethod()


def test_method_input(test_method):
    with pytest.raises(ValueError, match="Input parameters not set"):
        test_method.input  # noqa
