"""Testing of command line interface."""

from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner, Result

from hydroflows.cli.main import cli


class MockMethod:
    def __init__(self, file_in, file_out, **params):
        assert isinstance(file_in, str)
        assert isinstance(file_out, str)
        assert not params

    @classmethod
    def from_kwargs(cls, method, **kwargs):
        return cls(**kwargs)

    def run_with_checks(self):
        return "Mocked Method run called"


def test_cli_main(cli_obj: CliRunner):
    result: Result = cli_obj.invoke(cli, ["--help"], echo=True)
    assert result.exit_code == 0


def test_cli_run_help(cli_obj: CliRunner):
    result: Result = cli_obj.invoke(cli, ["run", "--help"], echo=True)
    assert result.exit_code == 0


def test_cli_run_method(cli_obj: CliRunner, monkeypatch: MonkeyPatch):
    # mock the Method class
    monkeypatch.setattr("hydroflows.cli.main.Method", MockMethod)

    kwargs = [
        "file_in=./file1.txt",
        "file_out=./file2.txt",
    ]

    # uses the MockMethod class above
    result: Result = cli_obj.invoke(
        cli, ["method", "test_method", "-v"] + kwargs, echo=True
    )
    assert result.exit_code == 0
