"""
HydroFlows Rule class.

Defines the relationship between inputs and outputs taking care of expansions as
forwarded from the Workflow class. Rule is agnositc across all Methods and so
requires a Method class as input.

"""

from typing import Dict, Optional

from ..methods.method import Method

FMT = ["snakemake"]

class Rule:
    """Define relationships between inputs and outputs."""

    def __init__(
        self,
        method: Method,
        wildcards: Dict = {},  # contains names that may also appear in input and output
        input: Optional[Dict] = {},
        output: Optional[Dict] = {},
        params: Optional[Dict] = {}
    ):
        """
        Initialize.

        Parameters
        ----------
        method : Hydroflows.Method
            subclass of Method
        wildcards : dict
        input
        output
        params
        """
        self.method = method
        self.wildcards = wildcards
        self.input = input  # keep this as dict
        self.output = output
        self.params = params
        self.validate()

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
        return ""

    def validate(self) -> None:
        """
        Expand all inputs and outputs and validates if these are compatible with method.

        Parameters
        ----------
        self :

        Returns
        -------
        None

        """
        # check if the inputs/outputs/params belong to provided method (using pydantic
        # and performing loops over wildcards).

        pass
