"""The command line interface for hydroflows.

We foresee the following commands:

- hydroflows run: run a single method from the methods submodule, e.g.,:
  hydroflows run build_wflow \
    --params param1 param2 \
    --inputs input1 input2 \
    --outputs output1

optional
- hydroflows init: initialize a new project
- hydroflows create: create a new workflow
"""

from pathlib import Path
from typing import Dict, Literal, Optional

import click

from hydroflows import __version__
from hydroflows.log import setuplog
from hydroflows.workflow.method import Method
from hydroflows.workflow.workflow import Workflow


# Copied from rasterio.rio.options
def _cb_key_val(ctx: click.Context, param: str, value: str) -> Dict[str, str]:
    """Convert key-value pairs to dictionary.

    click callback to validate `KEY1=VAL1 KEY2=VAL2` and collect
    in a dictionary like the one below, which is what the CLI function receives.
    If no value or `None` is received then an empty dictionary is returned.

        {
            'KEY1': 'VAL1',
            'KEY2': 'VAL2'
        }

    Note: `==VAL` breaks this as `str.split('=', 1)` is used.
    """
    if not value:
        return {}
    else:
        out = {}
        for pair in value:
            if "=" not in pair:
                raise click.BadParameter(
                    "Invalid syntax for KEY=VAL arg: {}".format(pair)
                )
            else:
                k, v = pair.split("=", 1)
                out[k] = None if v.lower() in ["none", "null", "nil", "nada"] else v
        return out


def print_license(ctx: click.Context, param: str, value: str) -> Optional[Dict]:
    """Print the license for hydroflows."""
    if not value:
        return {}
    click.echo("MIT License. See https://opensource.org/license/mit")
    ctx.exit()


def print_info(ctx: click.Context, param: str, value: str) -> Optional[Dict]:
    """Print a copyright statement for hydroflows."""
    if not value:
        return {}
    click.echo("hydroflows, Copyright Deltares")
    ctx.exit()


verbose_opt = click.option("--verbose", "-v", count=True, help="Increase verbosity.")
quiet_opt = click.option("--quiet", "-q", count=True, help="Decrease verbosity.")
overwrite_opt = click.option(
    "--overwrite",
    "-w",
    is_flag=True,
    default=False,
    help="Overwrite log message (instead of appending).",
)


@click.group()
@click.version_option(__version__, message="hydroflows version: %(version)s")
@click.option(
    "--license",
    default=False,
    is_flag=True,
    is_eager=True,
    help="Print license information for hydroflows",
    callback=print_license,
)
@click.option(
    "--info",
    default=False,
    is_flag=True,
    is_eager=True,
    help="Print information and version of hydroflows",
    callback=print_info,
)
@click.option("--debug/--no-debug", default=False, envvar="REPO_DEBUG")
@click.pass_context
def cli(ctx, info, license, debug):  # , quiet, verbose):
    """Command line interface for hydroflows."""
    if ctx.obj is None:
        ctx.obj = {}


@cli.command(short_help="Run a method with a set of key-word arguments.")
@click.argument("METHOD", type=str, nargs=1)
@click.argument(
    "KWARGS",
    nargs=-1,
    callback=_cb_key_val,
)
@click.option(
    "--dry_run", "--dryrun", is_flag=True, help="Perform a dry_run of the method."
)
@click.option(
    "--touch-output",
    is_flag=True,
    help="Create empty files at output location during dryrun.",
)
@click.pass_context
def method(
    ctx: click.Context,
    method: str,
    kwargs: Dict[str, str],
    dry_run: bool = False,
    touch_output: bool = False,
):
    """Run a method with a set of key-word arguments.

    RUNNER is the name of the method to run, e.g., 'build_wflow'.
    KWARGS is a list of key-value pairs, e.g., 'input=foo output=bar'.
    """
    logger = setuplog()
    try:
        method: Method = Method.from_kwargs(method, **kwargs)
        if dry_run:
            input_files = list(method.input.to_dict().values())
            if touch_output:
                method.dryrun(
                    input_files=input_files, missing_file_error=True, touch_output=True
                )
            else:
                method.dryrun(input_files=input_files, missing_file_error=True)
        else:
            method.run_with_checks()
    except Exception as e:
        logger.error(e)
        ctx.exit(1)


@cli.command(short_help="Create a workflow file.")
@click.argument(
    "WORKFLOW",
    type=click.Path(exists=True, file_okay=True),
)
# TODO support output dir requires adapting relative paths in the workflow file.
# for now we assume the workflow file is in the output dir.
# @click.argument(
#     "OUTPUT_DIR",
#     type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True),
# )
@click.option(
    "--fmt",
    required=False,
    type=click.Choice(["smk"]),
    help="Choose the format of the workflow file.",
    default="smk",
)
@click.pass_context
def create(
    ctx: click.Context,
    workflow: Path,
    # output_dir: Path,
    fmt: Literal["smk"] = "smk",
) -> None:
    """Create a workflow file.

    Parameters
    ----------
    WORKFLOW : Path
        The hydroflows workflow file to use as template.
    FORMAT : Literal["smk"]
        The format of the workflow file.
    """
    wf = Workflow.from_yaml(workflow)
    match fmt:
        case "smk":
            wf.to_snakemake(Path(workflow).with_suffix(".smk"))
        case _:
            click.echo(f"Error: Unknown format {fmt}")
            ctx.exit(1)


@cli.command(short_help="Run a workflow file.")
@click.argument(
    "WORKFLOW",
    type=click.Path(exists=True, file_okay=True),
)
@click.pass_context
def run(
    ctx: click.Context,
    workflow: Path,
) -> None:
    """Create a workflow file.

    Parameters
    ----------
    WORKFLOW : Path
        The hydroflows workflow file to use as template.
    """
    try:
        Workflow.from_yaml(workflow).run()
    except Exception as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


if __name__ == "__main__":
    cli()
