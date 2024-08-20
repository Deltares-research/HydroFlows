"""Pydantic models for method parameters."""

from pathlib import Path
from typing import Dict, List, Literal, Tuple, Type

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)

from hydroflows.workflow.reference import Ref


class Parameters(BaseModel):
    """Parameters class.

    This class is used to define the parameters (input, output and params) for a method.
    """

    model_config = ConfigDict(extra="forbid")

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
    def _resolve_refs(cls, data: Dict) -> Dict:
        """Resolve the references to other parameters."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, Ref):
                    data[key] = value.value
        return data

    def to_dict(
        self,
        mode: Literal["python", "json"] = "python",
        filter_types: Tuple[Type] = None,
        filter_keys: List = None,
        return_refs=False,
        posix_path=False,
        quote_str=False,
        exclude_ref_keys: List[str] = None,
        **kwargs,
    ) -> Dict:
        """Convert the parameters fields to a dictionary.

        Parameters
        ----------
        mode : Literal["python", "json"], optional
            The serialization mode, by default "python"
        filter_types : Tuple[Type], optional
            Filter the parameters by type, by default None
        filter_keys : List, optional
            Filter the parameters by key, by default None
        return_refs : bool, optional
            Return references instead of values, by default False
        posix_path : bool, optional
            Convert Path objects to posix paths (str), by default False
        quote_str : bool, optional
            Quote string values, by default False
        exclude_ref_keys : List[str], optional
            Do not transform these keys to references, by default None
        """
        kwargs = {"exclude_none": True, "mode": mode, **kwargs}
        parameters = self.model_dump(**kwargs)
        exclude_ref_keys = exclude_ref_keys or []
        out_dict = {}
        for k, v in parameters.items():
            org_val = getattr(self, k)
            if (filter_keys is not None and k not in filter_keys) or (
                filter_types is not None and not isinstance(org_val, filter_types)
            ):
                continue
            elif return_refs and k in self._refs and k not in exclude_ref_keys:
                # return cross-references (str)
                out_dict[k] = self._refs[k]
            elif posix_path and isinstance(org_val, Path):
                # convert Path to posix path;
                # NOTE this could also be done with a custom pydantic Serializer but then
                # all Path fields would need to be replaced by a custom annotated PathField
                out_dict[k] = org_val.as_posix()
                if quote_str:
                    out_dict[k] = f'"{out_dict[k]}"'
            elif quote_str and isinstance(org_val, str):
                out_dict[k] = f'"{v}"'
            else:
                out_dict[k] = v

        return out_dict
