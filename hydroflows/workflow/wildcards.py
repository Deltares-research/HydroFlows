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
    s: str | Path, wildcard_list: list[dict[str, str]]
) -> list[str | Path]:
    """Resolve wildcards in a string or path using a dictionary of values.

    With multiple wildcards, all possible combinations of values are created.

    Parameters
    ----------
    s : str | Path
        The string or path to resolve wildcards in.
    wildcards : list[dict[str, str]]
        A list of dictionaries with wildcard keys and value.
    """
    is_path = False
    if isinstance(s, Path):
        is_path = True
        s = s.as_posix()

    # Get the wildcards in the string
    wildcard_keys = get_wildcards(s)

    # If there are no wildcards in the string, return the string as is
    resolved_strings = []
    for wildcard_dict in wildcard_list:
        wc = {k: v for k, v in wildcard_dict.items() if k in wildcard_keys}
        if wc:
            resolved_strings.append(s.format(**wc))
        else:
            resolved_strings.append(s)

    if is_path:
        resolved_strings = [Path(p) for p in resolved_strings]
    return resolved_strings
