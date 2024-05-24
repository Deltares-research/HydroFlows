"""HydroFlows Method class.

A method is where the actual work of a rule happens.
It should have a name, inputs, and outputs, and optionally params.

All HydroFlow methods should inherit from this class and implement specific
validators and a run method.
"""

from pathlib import Path

from pydantic import BaseModel

__all__ = ["Method"]

# hydromt templates dir
PACKAGE_ROOT = Path(__file__).parent.parent
HYDROMT_CONFIG_DIR = PACKAGE_ROOT / "templates" / "workflow" / "hydromt_config"


class BaseParams(BaseModel):
    """Base rule for all parameters. Must be extended for rule-specific tasks."""

    pass


class Method(BaseModel):
    """Base method for all methods. Must be extended for rule-specific tasks."""

    # use pydantic models to (de)serialize/validate the input, output and params
    input: BaseModel
    output: BaseModel
    params: BaseParams = BaseParams()  # initialize when *all* parameters are optional

    def run(self) -> None:
        """Implement the rule logic here.

        This method is called when executing the rule.
        """
        # NOTE: this should be implemented in the specific rule
        # it can use input, output and params, e.g. self.input.file1
        # raise NotImplementedError
        return 1
