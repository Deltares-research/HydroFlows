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

import os
from pathlib import Path

import click

from .. import __version__, log
from ..methods import METHODS
from ..utils import copy_templates, create_folders


# Copied from rasterio.rio.options
def _cb_key_val(ctx, param, value):
    """Convert key-value pairs to dictionary.

    click callback to validate `--opt KEY1=VAL1 --opt KEY2=VAL2` and collect
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
            if '=' not in pair:
                raise click.BadParameter(
                    "Invalid syntax for KEY=VAL arg: {}".format(pair))
            else:
                k, v = pair.split('=', 1)
                k = k.lower()
                out[k] = None if v.lower() in ['none', 'null', 'nil', 'nada'] else v
        return out

def print_license(ctx, param, value):
    """Print the license for hydroflows."""
    if not value:
        return {}
    click.echo("MIT License. See https://opensource.org/license/mit")
    ctx.exit()


def print_info(ctx, param, value):
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
    help="Overwrite log message (instead of appending)."
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
@click.option(
    '--debug/--no-debug',
    default=False,
    envvar='REPO_DEBUG'
)
@click.pass_context
def cli(ctx, info, license, debug):  # , quiet, verbose):
    """Command line interface for hydroflows."""
    if ctx.obj is None:
        ctx.obj = {}


opt_input = click.option(
    '-i',
    '--input',
    multiple=True,
    callback=_cb_key_val,
    required=True,
)
opt_output = click.option(
    '-o',
    '--output',
    multiple=True,
    callback=_cb_key_val,
    required=True,
)
opt_params = click.option(
    '-p',
    '--params',
    multiple=True,
    callback=_cb_key_val,
    required=False,
)

@cli.command(short_help="Run a method with set inputs, outputs and parameters")
@click.argument(
    "RUNNER",
    type=str
)
@opt_input
@opt_output
@opt_params
@verbose_opt
@quiet_opt
@overwrite_opt
@click.pass_context
def run(ctx, runner, input, output, params, verbose, quiet, overwrite):
    """Run a method with set inputs, outputs and parameters."""
    append = not overwrite
    # print(overwrite)
    log_level = max(10, 30 - 10 * (verbose - quiet))
    logger = log.setuplog(
        f"run_{runner}",
        os.path.join(os.getcwd(), f"hydroflows_run_{runner}.log"),
        log_level=log_level,
        append=append,
    )
    if runner not in METHODS:
        raise ValueError("Method not implemented")
    try:
        # pdb.set_trace()
        logger.info(f"Input: {input}")
        logger.info(f"Parameters: {params}")
        logger.info(f"Output: {output}")

        if params:
            method = METHODS[runner](input=input, output=output, params=params)
        else:
            method = METHODS[runner](input=input, output=output)

        method.run()

    except Exception as e:
        logger.exception(e)  # catch and log errors
        raise
    finally:
        # close logger gracefully
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

@cli.command(short_help="Create a new project folder structure and copy templates")
@click.argument(
    "ROOT",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True),
)
@click.pass_context
def init(ctx, root: Path) -> None:
    """Initialize a new project."""
    create_folders(root)
    copy_templates(root)

if __name__ == "__main__":
    cli()
