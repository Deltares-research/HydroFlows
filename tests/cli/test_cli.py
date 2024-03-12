"""Testing of command line interface."""
import os

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




def test_cli_run_SUBCOMMAND(cli_obj):
    result = cli_obj.invoke(
        cli, [
            'run',
            'test_method',
            '--input',
            'file1=./file1.txt',
            '-i',
            'file2=./file2.txt',
            '--output',
            'file=./output.txt',
            '-v'
        ],
        echo=True
    )

    assert result.exit_code == 0
    # check if log file appears
    log_file = "hydroflows_run_test_method.log"
    assert os.path.isfile(log_file)
    # remove log file afterwards
    os.remove(log_file)
