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
    input: Dict
    output: Dict
    params: Dict


    def to_file(
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
        wildcards : Dict[str, List],
            expansion of wildcards for given inputs or outputs

        """

        raise NotImplementedError

    def run(self):
        """
        Model specific running method goes here

        Returns
        -------

        """
        # TODO: change into logger object
        print(f"Running rule with input {self.input} and params {self.params}")
        print(f"Writing output to {self.output}")
        self.input.file1

