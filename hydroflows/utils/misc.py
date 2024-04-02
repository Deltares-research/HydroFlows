"""Some miscellaneous util functions."""
import re


def compose_cli_list(
    data: list | tuple,
):
    """_summary_.

    _extended_summary_

    Parameters
    ----------
    data : list | tuple
        _description_
    """
    out_string = [
        f"'{item}'" for item in data
    ]
    return out_string


def decompose_cli_list(
    data: str,
):
    """_summary_.

    _extended_summary_

    Parameters
    ----------
    data : str
        _description_
    """
    pattern = r"'(.*?)'"
    components = re.findall(pattern, data)
    if not components:
        raise ValueError(f"{data} has no elements within apostrophes. \
Could not obtain any elements from it.")
    return components
