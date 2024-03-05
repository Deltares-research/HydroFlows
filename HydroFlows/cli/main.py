"""This script contains the command line interface for HydroFlows. 
We foresee the following commands:

- hf run: run a single rule specified in the rules submodule
          e.g. hf run build_wflow --params param1 param2 --inputs input1 input2 --outputs output1

optional
- hf init: initialize a new project
- hf create: create a new workflow
"""

import click
import json
import os

from .. import __version__
from pydantic import ValidationError


def print_license(ctx, param, value):
    if not value:
        return {}
    click.echo(f"MIT License. See https://opensource.org/license/mit")
    ctx.exit()


def print_info(ctx, param, value):
    if not value:
        return {}
    click.echo(f"HydroFlows, Copyright Deltares")
    ctx.exit()


verbose_opt = click.option("--verbose", "-v", count=True, help="Increase verbosity.")

@click.group()
@click.version_option(__version__, message="HydroFlows version: %(version)s")
@click.option(
    "--license",
    default=False,
    is_flag=True,
    is_eager=True,
    help="Print license information for HydroFlows",
    callback=print_license,
)
@click.option(
    "--info",
    default=False,
    is_flag=True,
    is_eager=True,
    help="Print information and version of HydroFlows",
    callback=print_info,
)
@click.option(
    '--debug/--no-debug',
    default=False,
    envvar='REPO_DEBUG'
)
@click.pass_context
def cli(ctx, info, license, debug):  # , quiet, verbose):
    """ Command line interface for HydroFlows """
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
@click.pass_context
def run(ctx, runner, input, output, params):
    raise NotImplementedError
    # check if runner is available


if __name__ == "__main__":
    cli()
