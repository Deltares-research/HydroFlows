"""Some parser utils to be used with pydantic validators."""

import re
from typing import List, Optional

__all__ = ["str_to_list", "get_wildcards"]


def str_to_list(v: str) -> list[str]:
    """Split comma and space separated string to list."""
    # remove whitespace and [] at the beginning and end
    v = v.strip("[] ")
    # split by comma but not inside quotes
    regex = r"[^,\s\"']+|\"([^\"]*)\"|'([^']*)'"
    if not any(re.findall(regex, v)):  # no commas: split by space
        # split by space but not inside quotes
        regex = r"[^\s\"']+|\"([^\"]*)\"|'([^']*)'"
    vlist = [m.group(1) or m.group(2) or m.group(0) for m in re.finditer(regex, v)]
    # strip whitespace and quotes from values
    return [v.strip("'\" ") for v in vlist]


def str_to_tuple(v: str) -> tuple[str, str]:
    """Convert a comma and space-separated string to a tuple."""
    # remove whitespace and () at the beginning and end
    v = v.strip("() ")
    # split by comma but not inside quotes
    regex = r"[^,\s\"']+|\"([^\"]*)\"|'([^']*)'"
    if not any(re.findall(regex, v)):  # no commas: split by space
        # split by space but not inside quotes
        regex = r"[^\s\"']+|\"([^\"]*)\"|'([^']*)'"
    # create a list from the matches, keeping quoted groups intact
    vlist = [m.group(1) or m.group(2) or m.group(0) for m in re.finditer(regex, v)]
    # strip whitespace and quotes from values
    clean_list = [val.strip("'\" ") for val in vlist]
    # return the list as a tuple
    return tuple(clean_list)


def get_wildcards(s, known_wildcards: Optional[List[str]] = None) -> List[str]:
    """Return a list of wildcards in the form of `{*}` from a string.

    Parameters
    ----------
    s : str
        The string to search for wildcards.
    known_wildcards : List[str], optional
        List of known wildcards, by default None
    """
    if known_wildcards is not None:
        # Define the regex pattern to match known wildcards
        pattern = r"\{" + "|".join(known_wildcards) + r"\}"
    else:
        # Define the regex pattern to match any wildcard "{*}"
        pattern = r"\{.*?\}"

    # Find all matches of the pattern in the string
    matches = re.findall(pattern, str(s))

    # Return list of matches with curly braces stripped
    return [str(wc).strip("{}") for wc in matches]
