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
            'SOME.SUBCOMMAND',
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

