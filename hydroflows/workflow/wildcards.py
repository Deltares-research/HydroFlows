"""Workflow wildcards module."""

import itertools
from logging import getLogger
from pathlib import Path

from pydantic import BaseModel

from hydroflows.utils.parsers import get_wildcards

logger = getLogger(__name__)


class Wildcards(BaseModel):
    """Wildcards class.

    This class is used to define the wildcards for the workflow.
    """

    wildcards: dict[str, list[str]] = {}
    """List of wildcard keys and values."""

    @property
    def names(self) -> list[str]:
        """Get the names of the wildcards."""
        return list(self.wildcards.keys())

    @property
    def values(self) -> list[list]:
        """Get the values of the wildcards."""
        return list(self.wildcards.values())

    def to_dict(self) -> dict[str, list]:
        """Convert the wildcards to a dictionary of names and values."""
        return self.model_dump()["wildcards"]

    def set(self, key: str, values: list[str]):
        """Add a wildcard."""
        key = str(key).lower()
        if key in self.wildcards and values != self.wildcards[key]:
            raise KeyError(f"Wildcard '{key}' already exists.")
        self.wildcards.update({key: values})
        logger.info(f"Added wildcard '{key}' with values: {values}")

    def get(self, key: str) -> list[str]:
        """Get the values of a wildcard."""
        key = str(key).lower()
        if key not in self.wildcards:
            raise KeyError(
                f"Wildcard '{key}' not found. "
                f"Available wildcards are: {', '.join(self.names)}"
            )
        return self.wildcards[key]


def wildcard_product(wildcards: dict[str, list[str]]) -> list[dict[str, str]]:
    """Get the product of wildcard values.

    Parameters
    ----------
    wildcards : dict[str, list[str]]
        The wildcards and values to get the product of.
    """
    wildcard_keys = list(wildcards.keys())
    return [
        dict(zip(wildcard_keys, values))
        for values in itertools.product(*[wildcards[wc] for wc in wildcard_keys])
    ]


def resolve_wildcards(
    s: str | Path, wildcards: dict[str, list[str] | str]
) -> list[str | Path] | str | Path:
    """Resolve wildcards in a string or path using a dictionary of values.

    With multiple wildcards, all possible combinations of values are created.

    Parameters
    ----------
    s : str | Path
        The string or path to resolve wildcards in.
    wildcards : dict[str, list[str]]
        The dictionary of wildcards and values.
    """
    # keep only wildcards in the string
    wildcards_in_string = get_wildcards(s)

    if not wildcards_in_string:
        return s

    is_path = False
    if isinstance(s, Path):
        is_path = True
        s = s.as_posix()

    # check if all wildcards are in the wildcards dict
    missing_wildcards = set(wildcards_in_string) - set(wildcards.keys())
    if missing_wildcards:
        missing_wildcards_str = ", ".join(missing_wildcards)
        raise KeyError(f"Wildcard values missing for: {missing_wildcards_str}")

    wildcards = {k: v for k, v in wildcards.items() if k in wildcards_in_string}
    single_value = all(isinstance(v, str) for v in wildcards.values())
    # make sure values are lists
    wildcards = {k: v if isinstance(v, list) else [v] for k, v in wildcards.items()}

    resolved_strings = []
    for wc in wildcard_product(wildcards):
        resolved_strings.append(s.format(**wc))

    if is_path:
        resolved_strings = [Path(p) for p in resolved_strings]

    if single_value:
        return resolved_strings[0]
    else:
        return resolved_strings
