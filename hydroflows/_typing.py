from typing import Dict, Union

from pydantic import BeforeValidator, Json
from typing_extensions import Annotated

from hydroflows.utils.parsers import str_to_list

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

JsonDict = Union[Dict, Json]

# WildcardPath = Annotated[
#     Path,
#     BeforeValidator(lambda x: Path(x) if isinstance(x, str) else x),
# ]
