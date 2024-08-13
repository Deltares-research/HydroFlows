"""Pydantic models for method parameters."""

from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, model_validator

from hydroflows.reference import Ref


class Parameters(BaseModel):
    """Parameters class.

    This class is used to define the parameters (input, output and params) for a method.
    """

    _refs: Dict[str, str] = {}
    """Dictionary of references to parameters of other rules or config items."""

    def __init__(self, **data) -> None:
        super().__init__(**data)

        # save references in _refs property
        for key, value in data.items():
            if isinstance(value, Ref):
                self._refs[key] = value.ref

    @model_validator(mode="before")
    @classmethod
    def _resolve_refs(cls, data):
        """Resolve the references to other parameters."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, Ref):
                    data[key] = value.value
        return data


class ReduceParameters(Parameters):
    """ReduceInput class.

    This class is used to define the input parameters for a reduce method.
    Parameters of type Path or str with wildcards are converted to lists.
    """

    _reduce_wildcards: List[str] = []

    def __init__(self, **data) -> None:
        super().__init__(**data)
        self._reduce_wildcards = data.get("_reduce_wildcards", [])

    @model_validator(mode="before")
    @classmethod
    def _validate_reduce_input(cls, data):
        """Convert Path or str with wildcards to list."""
        if isinstance(data, dict):
            for wildcard in data.get("_reduce_wildcards", []):
                wc_str = "{" + wildcard + "}"
                for key, value in data.items():
                    if isinstance(value, (Path, str)) and wc_str in str(value):
                        data[key] = [value]
        return data


# if __name__ == "__main__":
#     from hydroflows.workflow import Workflow

#     class Input(Parameters):
#         work_dir: Path

#     wf = Workflow()
#     wf.config = {"work_dir": "/path/to/work_dir"}

#     inp = Input(work_dir=Ref("config.work_dir", wf))
#     print(inp)
#     print(inp._refs)
