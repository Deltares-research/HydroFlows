"""
HydroFlows Rule class.

Defines the relationship between inputs and outputs taking care of expansions as
forwarded from the Workflow class. Rule is agnositc across all Methods and so
requires a Method class as input.

"""

from itertools import compress
from typing import Dict, Optional, Type

from pydantic import BaseModel, model_validator

from ..methods.method import Method

FMT = ["snakemake"]



class Rule(BaseModel):
    """Define relationships between inputs and outputs.

    Parameters
    ----------
    method : Hydroflows.Method
        subclass of Method
    wildcards : dict
    input
    output
    params

    """

    method: Type[Method]
    wildcards: Optional[list] = []  # contains names that may also appear in input and
    # output
    input: Optional[Dict] = {}
    output: Optional[Dict] = {}
    params: Optional[Dict] = {}
    expand: Optional[Dict] = {}

    @model_validator(mode="after")
    def validate_wildcards_input_output(self) -> 'Rule':
        """Validate input / output logic.

        Validate input and output logic and wildcards. Set expand input args where
        applicable. Input args that need expanding are args with a wildcard that does
        not appear in the outputs.

        Returns
        -------
        None

        """
        # create expand property
        self.expand = {}
        # per wildcard, check if exists in output, if so, all outputs should have it
        for wildcard in self.wildcards:
            # check if there is occurrence of wildcard per output
            has_wildcard_op = [
                f"{{{wildcard}}}" in o_v for o_k, o_v in self.output.items()
            ]
            # if there is any occurrence, then there must be occurrence for all
            # outputs (op)
            if any(has_wildcard_op):
                if not all(has_wildcard_op):
                    raise AssertionError(
                        f"Rule is not valid. Wildcard {wildcard} appears in at least "
                        f"one output, and therefore must appear in all outputs"
                    )
            # if wildcard does not appear in output, then check if it must be
            # expanded. Should happen when it appears in inputs (ip)
            if not(any(has_wildcard_op)):
                has_wildcard_ip = [
                    f"{{{wildcard}}}" in o_v for o_k, o_v in self.input.items()
                ]
                # if it appears, then do not expand, if it does not appear then expand
                self.expand[wildcard] = list(
                    compress(
                        self.input.keys(),
                        has_wildcard_ip
                    )
                )

    def parse(
        self,
        fmt: Optional[str] = "snakemake"
    ) -> str:
        """
        Parse rule into workflow snippet.

        Parameters
        ----------
        fmt : str, optional
            format in which to parse.

        Returns
        -------
        str

        """
        if fmt not in FMT:
            raise ValueError(f"fmt must be one of {FMT}")

        # ... to-be-completed
        raise NotImplementedError("Rule parsing is not yet implemented")


# placeholder for parser
def parse_input_snakemake(
        input: Optional[Dict] = {},
        wildcard: Optional[list] = [],
        expand: Optional[list] = []
):
    """Parse inputs to snakemake rule input section."""
    input_str = "\tinput:\n"
    # TODO: make parser
    return input_str
