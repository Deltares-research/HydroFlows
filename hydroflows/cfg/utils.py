"""Some HydroMT recipe utility."""

from typing import Any


def find_step_index(
    steps: list[dict[str, Any]],
    name: str,
) -> int | None:
    """Find the index of a step in the list of steps.

    Parameters
    ----------
    steps : list[dict[str, Any]]
        The steps.
    name : str
        The name of the step (setup method most often).

    Returns
    -------
    int | None
        The index if found.
    """
    idx = 0
    while idx < len(steps):
        if name in steps[idx]:
            return idx
        idx += 1
    return None
