"""Testing of command line interface."""
import os

import pytest

from hydroflows.cli.main import cli


def test_cli_main(cli_obj):
    result = cli_obj.invoke(
        cli, [
            '--help'
        ],
        echo=True
    )
    assert result.exit_code == 0


def test_cli_run_help(cli_obj):
    result = cli_obj.invoke(
        cli, [
            'run',
            '--help'
        ],
        echo=True
    )
    assert result.exit_code == 0



@pytest.mark.parametrize(
    "subcommand",
    [
        "SOME.SUBCOMMAND",
        "OTHER.SUBCOMMAND",
    ]
)
def test_cli_run_SUBCOMMAND(cli_obj, subcommand):
    result = cli_obj.invoke(
        cli, [
            'run',
            subcommand,
            '--input',
            {
                "file1": "/path/to/file1"
            },
            '--params',
            {
                "param1": 5,
                "param2": True
            },
            '--output',
            {
                "file2": "/path/to/file2",
                "file3": "/path/to/file3"
            },
            '-v'
        ],
        echo=True
    )

    assert result.exit_code == 0
    # check if log file appears
    log_file = f"hydroflows_run_{subcommand}.log"
    assert os.path.isfile(log_file)
    # remove log file afterwards
    os.remove(log_file)
