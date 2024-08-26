import pytest

from hydroflows.utils.parsers import get_wildcards, str_to_list


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


def test_no_wildcards():
    assert get_wildcards("This is a test string.") == []


def test_wildcards_present():
    assert get_wildcards("This is a {wildcard} test.") == ["wildcard"]
    assert get_wildcards("Multiple {wildcard1} and {wildcard2}.") == [
        "wildcard1",
        "wildcard2",
    ]


def test_known_wildcards():
    known_wildcards = ["wildcard1", "wildcard2"]
    assert get_wildcards("This is a {wildcard1} test.", known_wildcards) == [
        "wildcard1"
    ]
    assert get_wildcards("Multiple {wildcard1} and {wildcard2}.", known_wildcards) == [
        "wildcard1",
        "wildcard2",
    ]
    assert get_wildcards("Unknown {wildcard3} present.", known_wildcards) == []
