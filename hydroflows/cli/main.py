"""This script contains the command line interface for hydroflows.
We foresee the following commands:

- hydroflows run: run a single method specified in the methods submodule
          e.g. hydroflows run build_wflow --params param1 param2 --inputs input1 input2 --outputs output1

optional
- hydroflows init: initialize a new project
- hydroflows create: create a new workflow
"""

import click
import os

from .. import __version__, log


def print_license(ctx, param, value):
    if not value:
        return {}
    click.echo("MIT License. See https://opensource.org/license/mit")
    ctx.exit()


def print_info(ctx, param, value):
    if not value:
        return {}
    click.echo("hydroflows, Copyright Deltares")
    ctx.exit()


verbose_opt = click.option("--verbose", "-v", count=True, help="Increase verbosity.")
quiet_opt = click.option("--quiet", "-q", count=True, help="Decrease verbosity.")
overwrite_opt = click.option("--overwrite", "-w", is_flag=True, default=False, help="Overwrite log message (instead of appending).")

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
    """ Command line interface for hydroflows """
    if ctx.obj is None:
        ctx.obj = {}


opt_input = click.option(
    '-i',
    '--input',
    type=dict,
    required=True,
)
opt_output = click.option(
    '-o',
    '--output',
    type=dict,
    required=True,
)
opt_params = click.option(
    '-p',
    '--params',
    type=dict,
    required=False,
)

@cli.command(short_help="Run a workflow rule with set inputs, outputs and parameters")
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
    append = not overwrite
    # print(overwrite)
    log_level = max(10, 30 - 10 * (verbose - quiet))
    logger = log.setuplog(
        f"run_{runner}",
        os.path.join(os.getcwd(), f"hydroflows_run_{runner}.log"),
        log_level=log_level,
        append=append,
    )
    try:
        logger.info(f"Input: {input}")
        logger.info(f"Parameters: {params}")
        logger.info(f"Output: {output}")
        print(f"Input: {input}")
        # close logger file

        # raise NotImplementedError
        # check if runner is available
    except Exception as e:
        logger.exception(e)  # catch and log errors
        raise
    finally:
        # close logger gracefully
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


if __name__ == "__main__":
    cli()