import json

import pytest
from pydantic import TypeAdapter, ValidationError

from hydroflows._typing import (
    EventDatesDict,
    ListOfFloat,
    ListOfFloatOrInt,
    ListOfInt,
    ListOfStr,
    TupleOfInt,
)


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
    with pytest.raises(ValidationError):
        ta.validate_python(["1", "2.2", "3"])
    with pytest.raises(ValidationError):
        ta.validate_python([1, 2.2, 3])


def test_list_of_float():
    ta = TypeAdapter(ListOfFloat)
    assert ta.validate_python("1.0, 2.0, 3.0") == [1.0, 2.0, 3.0]
    assert ta.validate_python("[1.0 2.0 3.0]") == [1.0, 2.0, 3.0]
    assert ta.validate_python([1, 2.0, 3]) == [1.0, 2.0, 3.0]
    with pytest.raises(ValidationError):
        ta.validate_python("a, b, c")
    with pytest.raises(ValidationError):
        ta.validate_python([1, 2, 3, "a"])


def test_list_of_float_or_int():
    ta = TypeAdapter(ListOfFloatOrInt)
    assert ta.validate_python("1, 2.2, 3") == [1.0, 2.2, 3.0]
    assert ta.validate_python("[1.0 2.2 3.0]") == [1, 2.2, 3]
    assert ta.validate_python([1, 2.2, 3]) == [1, 2.2, 3.0]
    with pytest.raises(ValidationError):
        ta.validate_python([1, 2.2, 3, "a"])


def test_tuple_of_int():
    ta = TypeAdapter(TupleOfInt)
    assert ta.validate_python("(12, 6)") == (12, 6)
    assert ta.validate_python("(12, 6.0)") == (12, 6)
    assert ta.validate_python("[12, 6.0]") == (12, 6)
    with pytest.raises(ValidationError):
        ta.validate_python((12, 6.2))
    with pytest.raises(ValidationError):
        ta.validate_python((12, 6, 7))
    with pytest.raises(TypeError):
        ta.validate_python((12, 6), (11, 5))


def test_event_dates_dict():
    ta = TypeAdapter(EventDatesDict)

    dates = {
        "p_event1": {"startdate": "2005-03-04 09:00", "enddate": "2005-03-07 17:00"},
        "p_event2": {"startdate": "2030-03-04 09:00", "enddate": "2005-03-07 17:00"},
    }

    validated_python = ta.validate_python(dates)
    validated_json = ta.validate_python(json.dumps(dates))
    validated_json2 = ta.validate_python(f"{dates}")

    assert validated_python == validated_json
    assert validated_python == validated_json2
    with pytest.raises(ValidationError):
        ta.validate_python({"p_event1": {"startdate": "2005-03-04 09:00"}})
    with pytest.raises(ValidationError):
        ta.validate_python(
            {
                "p_event2": {
                    "startdate": "2030-03-04 09:00",
                    "enTdate": "2005-03-07 17:00",
                }
            }
        )
