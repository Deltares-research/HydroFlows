"""Wflow run method."""

import subprocess
from pathlib import Path

from pydantic import BaseModel, FilePath

from ..method import Method

__all__ = ["WflowRun"]


class Input(BaseModel):
    """Input parameters."""

    wflow_toml: FilePath


class Output(BaseModel):
    """Output parameters."""

    # TODO: should if this file is in the wflow toml
    wflow_output_timeseries: Path


class Params(BaseModel):
    """Parameters."""

    wflow_bin: Path
    julia_num_threads: int = 4


class WflowRun(Method):
    """Rule for running a Wflow model."""

    name: str = "wflow_run"
    params: Params
    input: Input
    output: Output

    def run(self):
        """Run the WflowRun method."""
        # Set environment variable JULIA_NUM_THREADS
        env = {"JULIA_NUM_THREADS": str(self.params.julia_num_threads)}

        # Path to the wflow_cli executable
        wflow_cli_path = self.params.wflow_bin

        # Command to run wflow_cli with the TOML file
        command = [wflow_cli_path, self.input.wflow_toml]

        # Call the executable using subprocess
        subprocess.run(command, env=env, check=True)
