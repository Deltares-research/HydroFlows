"""FIAT run rule/ submodule."""
import subprocess
from pathlib import Path

from pydantic import BaseModel, FilePath

from ..method import Method


class Input(BaseModel):
    """Input FIAT run params."""

    fiat_haz: FilePath
    fiat_cfg: FilePath


class Params(BaseModel):
    """FIAT run params."""

    fiat_bin: FilePath
    threads: int = 1


class Output(BaseModel):
    """Output FIAT run params."""

    fiat_out: Path


class FIATRun(Method):
    """Method for running a FIAT model."""

    name: str = "fiat_run"
    params: Params
    input: Input
    output: Output

    def run(self):
        """Run the FIAT run rule."""
        # Get basic info
        fiat_bin_path = self.params.fiat_bin
        fiat_cfg_path = self.input.fiat_cfg
        threads = self.params.threads

        # Setup the cli command
        command = [
            fiat_bin_path,
            "run",
            fiat_cfg_path,
            "-t",
            str(threads),
        ]

        # Execute the rule
        subprocess.run(command)
