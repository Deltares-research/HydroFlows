"""Run a method from snakemake."""

from typing import TYPE_CHECKING, Dict, Tuple

from hydroflows.workflow import Method

if TYPE_CHECKING:
    from snakemake.script import Snakemake


# method defined for correct type hinting
def unpack_snakemake() -> Tuple[str, Dict, Dict, Dict, Dict]:
    """Get snakemake object."""
    if "snakemake" not in globals():
        raise ValueError("This script must be run from snakemake.")

    # get snakemake object
    snakemake: Snakemake = globals()["snakemake"]

    # unpack snakemake object
    # input, output, and params are not dicts, but snakemake.io.Namedlist
    rule_id = snakemake.rule
    input = dict(snakemake.input)
    output = dict(snakemake.output)
    params = dict(snakemake.params)
    config = snakemake.config
    return rule_id, input, output, params, config


if __name__ == "__main__":
    # get and unpack snakemake object
    rule_id, input, output, params, config = unpack_snakemake()
    method_name = params.pop("_method_name", rule_id)
    dryrun = bool(config.get("dryrun", False))

    # initialize method
    method = Method.from_dict(
        name=method_name, input=input, output=output, params=params
    )

    # run
    if not dryrun:
        method.run_with_checks()
    else:
        method.dryrun(missing_file_error=True)
