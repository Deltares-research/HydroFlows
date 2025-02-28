"""test workflow wildcards module."""

import logging
from pathlib import Path

import pytest

from hydroflows.workflow.wildcards import Wildcards, resolve_wildcards, wildcard_product


def test_wildcards(caplog):
    """Test wildcards."""
    wildcards = Wildcards(
        wildcards={
            "wildcard1": ["value1", "value2"],
            "wildcard2": ["value3", "value4", "value5"],
        }
    )

    assert wildcards.names == ["wildcard1", "wildcard2"]
    assert wildcards.values == [["value1", "value2"], ["value3", "value4", "value5"]]
    assert wildcards.to_dict() == {
        "wildcard1": ["value1", "value2"],
        "wildcard2": ["value3", "value4", "value5"],
    }

    caplog.set_level(logging.INFO)
    wildcards.set("wildcard3", ["value6", "value7"])
    assert "Added wildcard 'wildcard3' with values: ['value6', 'value7']" in caplog.text
    assert wildcards.names == ["wildcard1", "wildcard2", "wildcard3"]
    assert wildcards.values == [
        ["value1", "value2"],
        ["value3", "value4", "value5"],
        ["value6", "value7"],
    ]
    assert wildcards.to_dict() == {
        "wildcard1": ["value1", "value2"],
        "wildcard2": ["value3", "value4", "value5"],
        "wildcard3": ["value6", "value7"],
    }

    assert wildcards.get("wildcard1") == ["value1", "value2"]
    assert wildcards.get("WILDCARD1") == ["value1", "value2"]
    assert wildcards.get("wildcard2") == ["value3", "value4", "value5"]
    assert wildcards.get("wildcard3") == ["value6", "value7"]

    with pytest.raises(KeyError, match="Wildcard 'wildcard4' not found."):
        wildcards.get("wildcard4")

    with pytest.raises(KeyError, match="Wildcard 'wildcard1' already exists."):
        wildcards.set("wildcard1", ["yy", "xx"])
    # with same values should not raise an error
    wildcards.set("wildcard1", wildcards.get("wildcard1"))


def test_wildcard_product():
    """Test wildcard product."""
    wildcards = {
        "wildcard1": ["value1", "value2"],
        "wildcard2": ["value3", "value4", "value5"],
    }
    product = wildcard_product(wildcards)
    assert len(product) == 6
    assert product[0] == {"wildcard1": "value1", "wildcard2": "value3"}
    assert product[5] == {"wildcard1": "value2", "wildcard2": "value5"}


def test_resolve_wildcards():
    wildcards = {
        "wildcard1": ["value1", "value2"],
        "wildcard2": ["value3", "value4"],
    }
    assert resolve_wildcards("This is a {wildcard1} test.", wildcards) == [
        "This is a value1 test.",
        "This is a value2 test.",
    ]

    assert set(
        resolve_wildcards("Multiple {wildcard1} and {wildcard2}.", wildcards)
    ) == set(
        [
            "Multiple value1 and value3.",
            "Multiple value1 and value4.",
            "Multiple value2 and value3.",
            "Multiple value2 and value4.",
        ]
    )

    # test with Path
    assert resolve_wildcards(
        Path("path/to/{wildcard1}/{wildcard2}.yml"), wildcards
    ) == [
        Path("path/to/value1/value3.yml"),
        Path("path/to/value1/value4.yml"),
        Path("path/to/value2/value3.yml"),
        Path("path/to/value2/value4.yml"),
    ]

    assert resolve_wildcards(
        Path("path/to/{wildcard1}/{wildcard2}.yml"),
        {"wildcard1": "value1", "wildcard2": "value2"},
    ) == Path("path/to/value1/value2.yml")

    with pytest.raises(KeyError, match="Wildcard values missing for: wildcard3."):
        resolve_wildcards("Unknown {wildcard3} present.", wildcards)
