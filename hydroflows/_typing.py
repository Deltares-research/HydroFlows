from pathlib import Path
from typing import Dict, List, Union

from pydantic import AfterValidator, BeforeValidator, Json
from typing_extensions import Annotated

from hydroflows.utils.parsers import get_wildcards, str_to_list

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

ListOfPath = Annotated[
    List[Path],
    BeforeValidator(lambda x: str_to_list(x) if isinstance(x, str) else x),
]

JsonDict = Union[Dict, Json]


def _check_path_has_wildcard(path: Union[Path, List[Path]]) -> Path:
    """Check if a path contains a wildcard."""
    if isinstance(path, Path) and not any(get_wildcards(path)):
        raise ValueError(f"Path {path} does not contain any wildcards")
    return path


WildcardPath = Annotated[
    Path,
    AfterValidator(_check_path_has_wildcard),
]
