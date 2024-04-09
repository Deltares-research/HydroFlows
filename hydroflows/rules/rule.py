"""
HydroFlows Rule class.

Defines the relationship between inputs and outputs taking care of expansions as
forwarded from the Workflow class. Rule is agnositc across all Methods and so
requires a Method class as input.

"""

from itertools import compress
from typing import Dict, Optional

from ..methods.method import Method

FMT = ["snakemake"]


# def parse_input_snakemake(
#         input: Optional[Dict] = {},
#         wildcard: Optional[list] = [],
#         expand: Optional[list] = []
# ):
#     """
#     Parse inputs to snakemake rule input section.
#
#     Parameters
#     ----------
#     input
#     wildcard
#     expand
#
#     Returns
#     -------
#
#     """
#     # input_str = "\tinput:\n"
#
#     #
#     # input:
#     #     nc_file_members = expand(
#     #         (root + "{basin_id}" + "/ensemble_cf/output_{member}_cf.nc"),
#     #         member=members,
#     #         allow_missing=True,
#     #     )
#     raise NotImplementedError

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
        self.expand = {}  # will be completed with validation
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
        """Validate wilcards.

        Verify wildcards inputs / outputs compatibility and expansion of inputs where
        needed.

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

    def validate_io(self) -> None:
        """Validate input / output logic.

        Validate input and output logic and wildcards. Set expand input args where
        applicable. Input args that need expanding are args with a wildcard that does
        not appear in the outputs.

        Returns
        -------
        None


        """
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
                        f"one output, and therefore must apppear in all outputs"
                    )
            # if wildcard does not appear in output, then check if it must be
            # expanded in appears in inputs (ip)
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

    def validate_methods(self) -> None:
        """Validate method."""
