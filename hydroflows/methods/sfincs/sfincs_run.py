"""Method for running a SFINCS model."""
import logging
import platform
import subprocess
from pathlib import Path
from typing import Literal, Optional

from pydantic import model_validator

from hydroflows._typing import FileDirPath
from hydroflows.methods.sfincs.sfincs_utils import get_sfincs_basemodel_root
from hydroflows.utils.docker_utils import fetch_docker_uid
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsRun", "Input", "Output", "Params"]

logger = logging.getLogger(__name__)


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`SfincsRun` method.
    """

    sfincs_inp: FileDirPath
    """The path to the SFINCS model configuration (inp) file."""


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`SfincsRun` method.
    """

    sfincs_map: FileDirPath
    """The path to the SFINCS sfincs_map.nc output file."""


class Params(Parameters):
    """Parameters.

    Instances of this class are used in the :py:class:`SfincsRun`
    method to define the required settings.
    """

    sfincs_exe: Optional[Path] = None
    """The path to SFINCS executable."""

    run_method: Literal["exe", "docker", "apptainer"] = "exe"
    """How to run the SFINCS model. The default is "exe", which runs the Windows executable.
    If 'docker' or 'aptainer' is specified, the model is run in a Docker or Apptainer container.
    """

    docker_tag: str = "sfincs-v2.2.0-col-dEze-Release"
    """The Docker tag to specify the version of the Docker image to use."""

    @model_validator(mode="after")
    def check_run_method(self) -> None:
        """Check if sfincs_exe is specified if run_method == 'exe'."""
        if self.run_method == "exe" and self.sfincs_exe is None:
            raise ValueError("sfincs_exe should be specified when run_method is 'exe'")
        return self


class SfincsRun(Method):
    """Method for running a SFINCS model.

    Parameters
    ----------
    sfincs_inp : str
        Path to the SFINCS input file.
    run_method : Literal["exe", "docker", "apptainer"], optional
        How to run the SFINCS model. The default is "exe", which runs the Windows executable.
        If 'docker' or 'apptainer' is specified, the model is run in a Docker or Apptainer container.
    sfincs_exe : Path, optional
        Path to the SFINCS Windows executable.
    **params
        Additional parameters to pass to the SfincsRun instance.
        See :py:class:`sfincs_run Params <hydroflows.methods.sfincs.sfincs_run.Params>`.

    See Also
    --------
    :py:class:`sfincs_run Input <hydroflows.methods.sfincs.sfincs_run.Input>`
    :py:class:`sfincs_run Output <hydroflows.methods.sfincs.sfincs_run.Output>`
    :py:class:`sfincs_run Params <hydroflows.methods.sfincs.sfincs_run.Params>`
    """

    name: str = "sfincs_run"

    _test_kwargs = {
        "sfincs_inp": Path("sfincs.inp"),
        "sfincs_exe": Path("sfincs.exe"),
    }

    def __init__(
        self,
        sfincs_inp: str,
        run_method: Literal["exe", "docker", "apptainer"] = "exe",
        sfincs_exe: Optional[Path] = None,
        **params,
    ) -> "SfincsRun":
        self.input: Input = Input(sfincs_inp=sfincs_inp)
        self.params: Params = Params(
            sfincs_exe=sfincs_exe, run_method=run_method, **params
        )

        self.output: Output = Output(
            sfincs_map=self.input.sfincs_inp.parent / "sfincs_map.nc"
        )

    def _run(self) -> None:
        """Run the SfincsRun method."""
        # make sure model_root is an absolute path
        model_root = self.input.sfincs_inp.parent.resolve()
        base_folder = get_sfincs_basemodel_root(model_root / "sfincs.inp")

        # set command to run depending on run_method
        if self.params.run_method == "exe":
            if platform.system() != "Windows":
                raise ValueError("sfince_exe only supported on Windows")
            sfincs_exe = self.params.sfincs_exe.resolve()
            if not sfincs_exe.is_file():
                raise FileNotFoundError(f"sfincs_exe not found: {sfincs_exe}")
            cmd = [str(sfincs_exe)]
        elif self.params.run_method == "docker":
            # Get user info to properly set ownership of files created by container
            # see: https://unix.stackexchange.com/a/627028
            (uid, gid) = fetch_docker_uid()
            cmd = [
                "docker",
                "run",
                f"-v{base_folder}://data",
                # f"-u{uid}:{gid}",
                "-w",
                f"/data/{model_root.relative_to(base_folder).as_posix()}",
                f"deltares/sfincs-cpu:{self.params.docker_tag}",
            ]
            if uid:
                cmd[3:3] = [f"-u{uid}:{gid}"]
        elif self.params.run_method == "apptainer":
            cmd = [
                "apptainer",
                "run",
                f"-B{base_folder}:/data",
                "--pwd",
                f"/data/{model_root.relative_to(base_folder).as_posix()}",
                f"docker://deltares/sfincs-cpu:{self.params.docker_tag}",
            ]

        # run & write log file
        log_file = model_root / "sfincs_log.txt"
        with open(log_file, "w") as f:
            proc = subprocess.run(
                cmd,
                cwd=model_root,
                stdout=f,
                stderr=f,
            )
            return_code = proc.returncode

        # check return code
        if return_code == 127:
            raise RuntimeError(
                f"{self.params.run_method} not found. Make sure it is installed, running and added to PATH."
            )
        elif return_code != 0:
            raise RuntimeError(f"SFINCS run failed with return code {return_code}")

        # check if "Simulation stopped" in log file
        with open(log_file, "r") as f:
            log = f.read()
            if "Simulation stopped" in log:
                raise RuntimeError(
                    f"SFINCS run failed. Check log file for details: {log_file}"
                )

        return None
