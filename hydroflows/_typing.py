import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Union

from pydantic import AfterValidator, BeforeValidator, Json
from typing_extensions import Annotated, TypedDict

from hydroflows.utils.parsers import (
    has_wildcards,
    str_to_list,
    str_to_list_nested,
    str_to_tuple,
)

ListOfStr = Annotated[
    list[str],
    BeforeValidator(lambda x: str_to_list(x) if isinstance(x, str) else x),
]

ListOfInt = Annotated[
    list[int],
    BeforeValidator(lambda x: str_to_list(x) if isinstance(x, str) else x),
]

ListOfFloat = Annotated[
    list[float],
    BeforeValidator(lambda x: str_to_list(x) if isinstance(x, str) else x),
]

ListOfListOfInt = Annotated[
    list[list[int]],
    BeforeValidator(lambda x: str_to_list_nested(x) if isinstance(x, str) else x),
]

TupleOfInt = Annotated[
    Tuple[int, int],
    BeforeValidator(
        lambda x: tuple(
            int(float(i)) if float(i).is_integer() else int(i) for i in str_to_tuple(x)
        )
        if isinstance(x, str)
        else x
    ),
]

ListOfPath = Annotated[
    List[Path],
    BeforeValidator(lambda x: str_to_list(x) if isinstance(x, str) else x),
]

JsonDict = Annotated[
    Union[Dict, Json],
    BeforeValidator(
        lambda x: json.loads(x.replace("'", '"')) if isinstance(x, str) else x
    ),
]


def _check_path_has_wildcard(path: Union[Path, List[Path]]) -> Path:
    """Check if a path contains a wildcard."""
    if isinstance(path, Path) and not has_wildcards(path):
        raise ValueError(f"Path {path} does not contain any wildcards")
    return path


WildcardPath = Annotated[
    Path,
    AfterValidator(_check_path_has_wildcard),
]

WildcardStr = Annotated[
    str,
    AfterValidator(_check_path_has_wildcard),
]

EventDatesDict = Annotated[
    Dict[
        str,
        TypedDict(
            "EventInfoDict",
            {
                "startdate": datetime,
                "enddate": datetime,
            },
        ),
    ],
    BeforeValidator(
        lambda x: json.loads(x.replace("'", '"')) if isinstance(x, str) else x
    ),
]

DataCatalogPath = Union[ListOfStr, ListOfPath, Path]


class folderpath(Path):
    """Subtype Path to indicate when parent folder is needed for workflow execution."""

    _flavour = type(Path())._flavour


def folderpath_validator(x: Path) -> folderpath:
    """Promote Path to folderpath type."""
    return folderpath(x)


FolderPath = Annotated[Path, AfterValidator(folderpath_validator)]


class outpath(Path):
    """Subclass Path to indicate path is used as root for output locations."""

    _flavour = type(Path())._flavour


def outpath_validator(x: Path) -> outpath:
    """Promote Path to outpath."""
    return outpath(x)


OutPath = Annotated[Path, AfterValidator(outpath_validator)]
