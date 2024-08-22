"""Some parser utils to be used with pydantic validators."""
import re


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
