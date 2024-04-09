"""HydroFlows Method class.

A method is where the actual work of a rule happens.
It should have a name, inputs, and outputs, and optionally params.

All HydroFlow methods should inherit from this class and implement specific
validators and a run method.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, FilePath

__all__ = ["Method"]

# NOTE these are just examples
# file1, file2 etc should be replaced by the actual inputs for the rule
class Input(BaseModel):
    file1: FilePath
    file2: FilePath


class Params(BaseModel):
    name: str
    arg1: int


class Output(BaseModel):
    file: FilePath


class Method(BaseModel):
    """Base method for all methods. Must be extended for rule-specific tasks."""

    input: Input
    output: Output
    params: Params


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
        raise NotImplementedError
