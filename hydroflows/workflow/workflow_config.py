"""Workflow config class."""

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict


class WorkflowConfig(BaseModel):
    """Workflow configuration class."""

    model_config = ConfigDict(extra="allow")

    # public fields with default values
    # TODO: add fields

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self.model_dump(**kwargs)

    def model_fields(self) -> List[str]:
        """Return the model fields."""
        return list(self.model_dump().keys())
