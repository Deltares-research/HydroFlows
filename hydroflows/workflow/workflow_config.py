"""Workflow config class."""

from pathlib import Path
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict


class WorkflowConfig(BaseModel):
    """Workflow configuration class."""

    model_config = ConfigDict(extra="allow")

    # public fields with default values
    # TODO: add fields

    def to_dict(
        self,
        mode: Literal["python", "json"] = "python",
        posix_path: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return the configuration as a dictionary.

        Parameters
        ----------
        mode : Literal["python", "json"], optional
            The serialization mode, by default "python"
        posix_path : bool, optional
            Convert Path objects to posix paths (str), by default False
        """
        kwargs = {"exclude_none": True, "mode": mode, **kwargs}
        conf = self.model_dump(**kwargs)
        for k in conf.keys():
            org_val = getattr(self, k)
            if posix_path and isinstance(org_val, Path):
                conf[k] = org_val.as_posix()
            elif posix_path and isinstance(org_val, list):
                conf[k] = [v.as_posix() if isinstance(v, Path) else v for v in org_val]
        return conf

    def model_fields(self) -> List[str]:
        """Return the model fields."""
        return list(self.model_dump().keys())
