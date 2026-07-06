"""Simple reader functionality for HydroMT build/ update recipes."""

import io
import re
from pathlib import Path
from typing import Any

import yaml

PAT = re.compile(r"(\<\w+\>)")


def read_recipe(
    file: Path | str,
    settings: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """Read HydroMT build/ update recipe.

    Parameters
    ----------
    file : Path | str
        The path to the recipe file.
    settings : dict[str, Any] | None, optional
        Settings connected to the placeholders in in the recipe file, by default None.

    Returns
    -------
    tuple[str, dict[str, Any], list[dict[str, Any]]]
        The name of the model, model settings & model setup steps.
    """
    with open(file, mode="r") as f:
        data = f.read()

    # Find all placeholders
    placeholders: list[str] = re.findall(PAT, data)
    placeholders = list(set(placeholders))

    settings = settings or {}
    # Check if all are set in the settings
    check = [
        item.strip("<>") for item in placeholders if item.strip("<>") not in settings
    ]
    if not len(check) == 0:
        raise KeyError(f"{check} placeholders not found in settings")

    # Replace the values in the recipe
    for key in placeholders:
        data = data.replace(key, str(settings[key.strip("<>")]))

    # Read in a buffer to be fed to yaml
    buf = io.StringIO()
    buf.write(data)
    buf.seek(0)

    # Read
    recipe: dict[str, Any] = yaml.safe_load(buf)

    # Return the info
    return recipe.get("modeltype"), recipe.get("global", {}), recipe.get("steps")
