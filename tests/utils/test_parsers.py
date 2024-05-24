import pytest

from hydroflows.utils.parsers import str_to_list


@pytest.mark.parametrize(
    ("str_list", "parsed_list"),
    [
        ("", []),
        ("a,b, c", ["a", "b", "c"]),
        ("a", ["a"]),
        ("[a, b]", ["a", "b"]),
        ("a b", ["a", "b"]),
        ("a, 'b'", ["a", "b"]),
        # comma seperated, comma and space in quotes
        ("a, 'a/b/, c.yml'", ["a", "a/b/, c.yml"]),
        # space seperated, comma and space in quotes
        ("a 'a/b/, c.yml'", ["a", "a/b/, c.yml"]),
    ],
)
def test_hydromt_params(str_list, parsed_list):
    """Test ParamsHydromt."""
    assert str_to_list(str_list) == parsed_list
