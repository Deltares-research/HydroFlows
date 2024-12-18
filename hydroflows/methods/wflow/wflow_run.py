"""Wflow run method."""

import subprocess
from pathlib import Path
from typing import Literal, Optional

from pydantic import model_validator

from hydroflows.methods.wflow.wflow_utils import get_wflow_basemodel_root
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

    run_method: Literal["exe", "docker", "julia", "apptainer"] = "exe"
    """How to run wflow. Options are 'exe' for running the executable directly (only on Windows),
    'docker' or 'apptainer' for running the model in a container."""

    wflow_bin: Optional[Path] = None
    """The path to the wflow executable."""

    julia_num_threads: int = 4
    """The number of the threads to be used from Julia."""

    docker_tag: str = "v0.8.1"
    """The Docker tag to specify the version of the Docker image to use."""

    @model_validator(mode="after")
    def check_wflow_bin(self):
        """Check the Wflow binary path."""
        if self.wflow_bin is None and self.run_method == "exe":
            raise ValueError(
                "Path to the Wflow executable is required when running Wflow as an executable."
            )
        return self


class WflowRun(Method):
    """Rule for running a Wflow model."""

    name: str = "wflow_run"

    _test_kwargs = {
        "wflow_toml": Path("wflow.toml"),
        "wflow_bin": Path("wflow_cli.exe"),
    }

    def __init__(
        self,
        wflow_toml: Path,
        run_method: Literal["exe", "docker", "julia", "apptainer"] = "exe",
        wflow_bin: Optional[Path] = None,
        **params,
    ) -> "WflowRun":
        """Create and validate a WflowRun instance.

        Parameters
        ----------
        wflow_toml : Path
            The file path to the Wflow (toml) configuration file.
        run_method : Literal["exe", "docker", "apptainer"]
            How to run Wflow. Options are 'exe' for running the executable directly (only on Windows),
            'docker' or 'apptainer' for running the model in a container.
        wflow_bin : Path
            The path to the Wflow executable
        **params
            Additional parameters to pass to the WflowRun Params instance.
            See :py:class:`wflow_run Params <hydroflows.methods.wflow.wflow_run.Params>`.

        See Also
        --------
        :py:class:`wflow_run Input <hydroflows.methods.wflow.wflow_run.Input>`
        :py:class:`wflow_run Output <hydroflows.methods.wflow.wflow_run.Output>`
        :py:class:`wflow_run Params <hydroflows.methods.wflow.wflow_run.Params>`
        """
        self.params: Params = Params(
            wflow_bin=wflow_bin, run_method=run_method, **params
        )
        self.input: Input = Input(wflow_toml=wflow_toml)
        self.output: Output = Output(
            wflow_output_timeseries=self.input.wflow_toml.parent
            / "run_default"
            / "output_scalar.nc"
        )

    def run(self):
        """Run the WflowRun method."""
        # Set environment variable JULIA_NUM_THREADS
        nthreads = str(self.params.julia_num_threads)
        wflow_toml = self.input.wflow_toml.resolve()
        base_folder = get_wflow_basemodel_root(wflow_toml=wflow_toml).as_posix()
        wflow_toml = wflow_toml.relative_to(base_folder).as_posix()

        env = None
        # Path to the wflow_cli executable
        if self.params.run_method == "exe":
            # Command to run wflow_cli with the TOML file
            command = [self.params.wflow_bin.as_posix(), wflow_toml]
            env = {"JULIA_NUM_THREADS": nthreads}
        elif self.params.run_method == "julia":
            command = [
                "julia",
                "-t",
                nthreads,
                "-e",
                "using Wflow; Wflow.run()",
                wflow_toml,
            ]
        elif self.params.run_method == "docker":
            command = [
                "docker",
                "run",
                f"-v{base_folder}://data",
                "-e",
                f"JULIA_NUM_THREADS={nthreads}",
                f"deltares/wflow:{self.params.docker_tag}",
                f"//data/{wflow_toml}",
            ]
        elif self.params.run_method == "apptainer":
            command = [
                "apptainer",
                "run",
                f"-B{base_folder}://data",
                "--env",
                f"JULIA_NUM_THREADS={nthreads}",
                f"docker://deltares/wflow:{self.params.docker_tag}",
                f"//data/{wflow_toml}",
            ]

        # Call the executable using subprocess
        subprocess.run(command, env=env, check=True, cwd=base_folder)
