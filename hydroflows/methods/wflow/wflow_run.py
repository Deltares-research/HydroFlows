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

    wflow_bin: Optional[Path] = None
    """The path to the wflow executable."""

    wflow_julia: bool = False
    """Whether to run the Wflow model from a Julia environment."""

    julia_num_threads: int = 4
    """The number of the threads to be used from Julia."""

    vm: Optional[Literal["docker", "singularity"]] = None
    """The virtual machine environment to use."""

    docker_tag: str = "v0.8.1"
    """The Docker tag to specify the version of the Docker image to use."""

    @model_validator(mode="after")
    def check_wflow_bin(self):
        """Check the Wflow binary path."""
        if self.wflow_bin is None and not self.wflow_julia and self.vm is None:
            raise ValueError("Specify valid method for running WFLOW")
        # if self.wflow_julia:
        #     return
        # if self.wflow_bin is None:
        #     raise ValueError("Wflow binary path is required.")


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
        wflow_bin: Optional[Path] = None,
        wflow_julia: bool = False,
        **params,
    ) -> "WflowRun":
        """Create and validate a WflowRun instance.

        Parameters
        ----------
        wflow_toml : Path
            The file path to the Wflow (toml) configuration file.
        wflow_bin : Path
            The path to the Wflow executable
        wflow_julia : bool
            Whether to run the Wflow model from a Julia environment
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
            wflow_bin=wflow_bin, wflow_julia=wflow_julia, **params
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
        env = {"JULIA_NUM_THREADS": str(self.params.julia_num_threads)}

        wflow_toml = self.input.wflow_toml.as_posix()
        # Path to the wflow_cli executable
        if self.params.wflow_julia:
            # julia -e 'using Wflow; Wflow.run()'
            command = ["julia", "-e", "using Wflow; Wflow.run()", wflow_toml]
        elif self.params.vm is not None:
            wflow_toml = self.input.wflow_toml.resolve()
            base_folder = get_wflow_basemodel_root(wflow_toml=wflow_toml)

            command = [
                "docker",
                "run",
                f"-v{base_folder}://data",
                "-e",
                f"JULIA_NUM_THREADS={env['JULIA_NUM_THREADS']}"
                f"deltares/wflow:{self.params.docker_tag}",
                f"//data/{wflow_toml.relative_to(base_folder).as_posix()}",
            ]
        else:
            # Command to run wflow_cli with the TOML file
            command = [self.params.wflow_bin.as_posix(), wflow_toml]

        # Call the executable using subprocess
        subprocess.run(command, env=env, check=True)
