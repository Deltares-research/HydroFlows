"""Wflow run method."""

import subprocess
from pathlib import Path

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["WflowRun"]


class Input(Parameters):
    """Input parameters for the :py:class:`WflowRun` method."""

    wflow_toml: Path
    """The file path to the Wflow (toml) configuration file from the
    Wflow model that needs to be run."""


class Output(Parameters):
    """Output parameters for the :py:class:`WflowRun` method."""

    # TODO: if this file is in the wflow toml
    wflow_output_timeseries: Path
    """The path to the generated Wflow output timeseries. Note that
    the output file should be in the Wflow toml configuration, for
    example, in case that a model was updated using the
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowUpdateForcing`
    method and includes Sfincs source outflow locations (built using the
    :py:class:`hydroflows.methods.wflow.wflow_update_forcing.WflowBuild` method),
    the file should be named as output_scalar.nc."""


class Params(Parameters):
    """Parameters for the :py:class:`WflowRun`."""

    wflow_bin: Path
    """The path to the wflow executable."""

    julia_num_threads: int = 4
    """The number of the threads to be used from Julia."""


class WflowRun(Method):
    """Rule for running a Wflow model."""

    name: str = "wflow_run"

    def __init__(self, wflow_toml: Path, **params) -> "WflowRun":
        """Create and validate a WflowRun instance.

        Parameters
        ----------
        wflow_toml : Path
            The file path to the Wflow (toml) configuration file.
        **params
            Additional parameters to pass to the WflowRun Params instance.
            See :py:class:`wflow_run Params <hydroflows.methods.wflow.wflow_run.Params>`.

        See Also
        --------
        :py:class:`wflow_run Input <hydroflows.methods.wflow.wflow_run.Input>`
        :py:class:`wflow_run Output <hydroflows.methods.wflow.wflow_run.Output>`
        :py:class:`wflow_run Params <hydroflows.methods.wflow.wflow_run.Params>`
        """
        self.params: Params = Params(**params)
        self.input: Input = Input(wflow_toml=wflow_toml)
        self.output: Output = Output(
            wflow_output_timeseries=self.input.wflow_toml.parent
            / "run_default"
            / "output_scalar.nc"
        )

    def run(self):
        """Run the WflowRun method."""
        # Set environment variable JULIA_NUM_THREADS
        env = {"JULIA_NUM_THREADS": str(self.params.julia_num_threads)}

        # Path to the wflow_cli executable
        wflow_cli_path = self.params.wflow_bin

        # Command to run wflow_cli with the TOML file
        command = [str(wflow_cli_path), str(self.input.wflow_toml)]

        # Call the executable using subprocess
        subprocess.run(command, env=env, check=True)
