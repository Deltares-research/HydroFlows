"""This script contains the Rule class, which is the main class for
defining rules in HydroFlows. A rule the basic unit in a workflow 
and should have a name, inputs, and outputs, and optionally params.
The goal of the Rule class is to validate these and hold the intelligence 
for running the rule. 

All HydroFlow rules should inherit from this class and implement specific
validators and a run method.

Later we may want to add common methods to parse rules to certain formats, e.g. smk, or cwl.
"""

from pydantic import BaseModel, FilePath
from typing import Dict, List, Optional

__all__ = ["Rule"]

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


class Rule(BaseModel):
    """
    Base rule to rule them all. Must be extended to rule-specific e.g. for running models, pre / postprocessing
    """
    input: Input
    output: Output
    params: Params


    def to_str(
        self,
        format: str ="snakemake",
        wildcards: Optional[Dict[str, List]] = {}
    ):
        """
        Parses rule to a string, suitable for a certain language

        Returns
        -------
        format : str
            selected format for output
        wildcards : Dict[str, List], optional
            expansion of wildcards for given inputs or outputs

        """

        raise NotImplementedError

    def run(self) -> None:
        """
        The rule logic should be implemented here. 
        This method called when executing the rule.
        """
        # NOTE: this should be implemented in the specific rule
        # it can use input, output and params, e.g. self.input.file1
        raise NotImplementedError

