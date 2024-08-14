"""Pydantic models for method parameters."""

from typing import Dict, List, Tuple, Type

from pydantic import BaseModel, model_validator

from hydroflows.workflow.reference import Ref


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
    def _resolve_refs(cls, data: Dict):
        """Resolve the references to other parameters."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, Ref):
                    data[key] = value.value
        return data

    def to_dict(
        self,
        filter_types: Tuple[Type] = None,
        filter_keys: List = None,
        return_refs=False,
        **kwargs,
    ) -> Dict:
        """Convert the parameters to a dictionary."""
        kwargs = {"exclude_none": True, **kwargs}
        out_dict = self.model_dump(**kwargs)
        if filter_types is not None:
            out_dict = {
                k: v for k, v in out_dict.items() if isinstance(v, filter_types)
            }
        if filter_keys is not None:
            out_dict = {k: v for k, v in out_dict.items() if k in filter_keys}
        # return cross-references (str) if requested
        # should be after filter_types
        if return_refs:
            out_dict = {k: self._refs.get(k, v) for k, v in out_dict.items()}
        return out_dict


# class ReduceParameters(Parameters):
#     """ReduceInput class.

#     This class is used to define the input parameters for a reduce method.
#     Parameters of type Path or str with wildcards are converted to lists.
#     """

#     _reduce_wildcards: List[str] = []

#     def __init__(self, **data) -> None:
#         super().__init__(**data)
#         self._reduce_wildcards = data.get("_reduce_wildcards", [])

#     @model_validator(mode="before")
#     @classmethod
#     def _validate_reduce_input(cls, data):
#         """Convert Path or str with wildcards to list."""
#         if isinstance(data, dict):
#             for wildcard in data.get("_reduce_wildcards", []):
#                 wc_str = "{" + wildcard + "}"
#                 for key, value in data.items():
#                     if isinstance(value, (Path, Ref, str)) and wc_str in str(value):
#                         data[key] = [value]
#         return data

# def _check_type(value, types, multiple=True) -> bool:
#     """Check if a value is of a certain type. If multiple, check if all values are of a certain type."""
#     if multiple and isinstance(value, (list, set)):
#         return all(isinstance(v, types) for v in value)
#     else:
#         return isinstance(value, types)

# if __name__ == "__main__":
#     from hydroflows.workflow import Workflow

#     class Input(Parameters):
#         work_dir: Path

#     wf = Workflow()
#     wf.config = {"work_dir": "/path/to/work_dir"}

#     inp = Input(work_dir=Ref("config.work_dir", wf))
#     print(inp)
#     print(inp._refs)
