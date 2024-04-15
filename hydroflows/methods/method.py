"""HydroFlows Method class.

A method is where the actual work of a rule happens.
It should have a name, inputs, and outputs, and optionally params.

All HydroFlow methods should inherit from this class and implement specific
validators and a run method.
"""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel

from hydroflows.methods._validators import ParamsHydromt

__all__ = ["Method"]

# hydromt templates dir
PACKAGE_ROOT = Path(__file__).parent.parent
HYDROMT_CONFIG_DIR = PACKAGE_ROOT / "templates" / "workflow" / "hydromt_config"


class Method(BaseModel):
    """Base method for all methods. Must be extended for rule-specific tasks."""

    # use pydantic models to (de)serialize the input, output and params
    input: BaseModel
    output: BaseModel
    params: BaseModel = ParamsHydromt()  # optional

    def to_str(
        self,
        wildcards: Optional[Dict[str, List]] = {}
    ):
        """Parse rule to a string, suitable for a certain language.

        Parameters
        ----------
        format : str
            selected format for output
        wildcards : Dict[str, List], optional
            expansion of wildcards for given inputs or outputs

        """
        raise NotImplementedError

    def run(self) -> None:
        """Implement the rule logic here.

        This method is called when executing the rule.
        """
        # NOTE: this should be implemented in the specific rule
        # it can use input, output and params, e.g. self.input.file1
        # raise NotImplementedError
        return 1
