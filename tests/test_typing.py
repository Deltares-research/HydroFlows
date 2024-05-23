import pytest
from pydantic import TypeAdapter, ValidationError

from hydroflows._typing import ListOfFloat, ListOfInt, ListOfStr


def test_list_of_str():
    ta = TypeAdapter(ListOfStr)
    assert ta.validate_python("a, b, c") == ["a", "b", "c"]
    assert ta.validate_python(["a", "b", "c"]) == ["a", "b", "c"]
    with pytest.raises(ValidationError):
        ta.validate_python(1)
    with pytest.raises(ValidationError):
        ta.validate_python([1, 2, 3])


def test_list_of_int():
    ta = TypeAdapter(ListOfInt)
    assert ta.validate_python("1, 2, 3") == [1, 2, 3]
    assert ta.validate_python("[1 2 3]") == [1, 2, 3]
    assert ta.validate_python(["1", "2.0", "3"]) == [1, 2, 3]
    with pytest.raises(ValidationError):
        ta.validate_python("a, b, c")
    with pytest.raises(ValidationError):
        ta.validate_python(["a", "b", "c"])


def test_list_of_float():
    ta = TypeAdapter(ListOfFloat)
    assert ta.validate_python("1.0, 2.0, 3.0") == [1.0, 2.0, 3.0]
    assert ta.validate_python("[1.0 2.0 3.0]") == [1.0, 2.0, 3.0]
    assert ta.validate_python([1, 2.0, 3]) == [1.0, 2.0, 3.0]
    with pytest.raises(ValidationError):
        ta.validate_python("a, b, c")
    with pytest.raises(ValidationError):
        ta.validate_python([1, 2, 3, "a"])
