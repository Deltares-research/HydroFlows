"""Utils to help parsing to CWL."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def map_cwl_types(input: Any) -> Dict[str, str]:
    """Map variable to cwl type and value.

    Parameters
    ----------
    input : Any
        Variable to map

    Returns
    -------
    Dict[str,str]
        Dict containing variable CWL type (used in both rule and workflow files) and its value (used to generate config file)

    Raises
    ------
    TypeError
        Raised when an array has elements with mixed types.
    TypeError
        Raised when a variable type could not parsed to CWL equivalent. Parsing to CWL string is tried as default.
    """
    out = {}
    match input:
        case bool():
            # Bool on out CLI is passed as a string
            out["type"] = "string"
            out["value"] = f"{str(input)}"
        case Path():
            if "{" in input.as_posix():
                # If path contains wildcard, input is array
                # Not yet seen a case where 'value' is needed here
                out["type"] = "File[]"
            if input.suffix:
                out["type"] = "File"
                out["value"] = {"class": "File", "path": input.as_posix()}
            elif input.exists():
                out["type"] = "Directory"
                out["value"] = {"class": "Directory", "path": input.as_posix()}
            else:
                out["type"] = "string"
                out["value"] = f"{input.as_posix()}"
        case str():
            if "/" in input:
                # In case a file path is passed as string
                out["type"] = "File"
                out["value"] = {"class": "File", "path": input}
            else:
                out["type"] = "string"
                out["value"] = f"{input}"
        case list():
            if all(isinstance(item, str) for item in input):
                out["type"] = "string[]"
                out["value"] = [f"{item}" for item in input]
            elif all(isinstance(item, Path) and item.suffix for item in input):
                out["type"] = "File[]"
                out["value"] = [
                    {"class": "File", "path": item.as_posix()} for item in input
                ]
            elif all(isinstance(item, Path) for item in input):
                out["type"] = "string[]"
                out["value"] = [item.as_posix() for item in input]
            elif all(isinstance(item, float) for item in input):
                out["type"] = "float[]"
                out["value"] = input
            elif all(isinstance(item, int) for item in input):
                # type int[] gave issues somewhere with parsing method inputs
                out["type"] = "float[]"
                out["value"] = input
            else:
                raise TypeError("No lists with mixed typed elements allowed!")
            # Translates array input to string on CLI
            out["separator"] = '", "'
        case float():
            out["type"] = "float"
            out["value"] = input
        case int():
            # type int gave issues somewhere with parsing method inputs
            out["type"] = "float"
            out["value"] = input
        case datetime():
            out["type"] = "string"
            out["value"] = f"{str(input)}"
        case _:
            try:
                out["type"] = "string"
                out["value"] = f"{str(input)}"
            except TypeError:
                raise TypeError(f"type {type(input)} could not be parsed.")
    return out
