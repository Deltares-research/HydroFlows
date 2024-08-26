"""Run a method from snakemake."""

from typing import TYPE_CHECKING, Dict

from hydroflows.workflow import Method

if TYPE_CHECKING:
    from snakemake.script import Snakemake


def get_snakemake() -> "Snakemake":
    """Get snakemake object."""
    if "snakemake" not in globals():
        raise ValueError("This script must be run from snakemake.")

    snakemake: Snakemake = globals()["snakemake"]
    return snakemake


if __name__ == "__main__":
    # unpack snakemake object
    snakemake = get_snakemake()
    input: Dict = snakemake.input
    output: Dict = snakemake.output
    params: Dict = snakemake.params
    config: Dict = snakemake.config
    method_name = params.get("_method_name", snakemake.rule)
    dryrun: bool = bool(config.get("dryrun", False))

    # initialize method
    method = Method.from_dict(
        name=method_name, input=input, output=output, params=params
    )

    # run
    if not dryrun:
        method.run_with_checks()
    else:
        method.dryrun(missing_file_error=True)
