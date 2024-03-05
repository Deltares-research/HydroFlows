from HydroFlows.cli.main import cli


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


