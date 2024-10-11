"""Utility of the FIAT methods."""
import re


def new_column_headers(
    columns: list | tuple,
    simple: bool = False,
):
    """Set the headers in the format of newer FIAT versions.

    Once HydroMT-FIAT has this functionality, this can be deleted.

    Parameters
    ----------
    columns : list | tuple
        The columns headers of the exposure data.
    simple : bool, optional
        Whether to return a simple conversion, i.e. everything lower case and
        whitespaces replaced by underscores. By default False.
    """
    new = dict(
        zip(
            columns,
            [item.lower().replace(" ", "_") for item in columns],
        )
    )
    if simple == True:
        return new

    # Update these headers which do not translate simply
    new.update(
        {
            "Extraction Method": "extract_method",
            "Ground Elevation": "ground_elevtn",
            "Ground Floor Height": "ground_flht",
        }
    )

    # Focus on the vulnerability functions headers
    re_fn = re.compile(r"^(.*)\sFunction:\s+(.*)$")
    re_max = re.compile(r"^Max Potential\s+(.*):\s+(.*)$")

    fn = {}
    for pattern, new_pattern in ((re_fn, "fn_{}_{}"), (re_max, "max_{}_{}")):
        found = list(filter(pattern.match, columns))
        for f in found:
            x = pattern.findall(f)
            string = new_pattern.format(*[item.lower() for item in x[0]])
            fn[f] = string

    new.update(fn)

    return new
