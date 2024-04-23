"""SFINCS run method."""

import platform
import subprocess
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, FilePath

from ..method import Method

__all__ = ["SfincsRun"]


class Input(BaseModel):
    """Input parameters."""

    sfincs_inp: FilePath


class Output(BaseModel):
    """Output parameters."""

    sfincs_map: Path


class Params(BaseModel):
    """Parameters."""

    sfincs_exe: Optional[Path] = None
    vm: Optional[Literal["docker", "singularity"]] = None
    docker_tag: str = "latest"


class SfincsRun(Method):
    """Rule for running a SFINCS model."""

    name: str = "sfincs_run"
    params: Params  # params.sfincs_exe required
    input: Input
    output: Output

    def run(self) -> None:
        """Run the SFINCS model."""
        # make sure model_root is an absolute path
        model_root = self.input.sfincs_inp.parent.resolve()

        # set command to run depending on OS and VM
        if self.params.sfincs_exe is not None and platform.system() == "Windows":
            sfincs_exe = self.params.sfincs_exe.resolve()
            if not sfincs_exe.is_file():
                raise FileNotFoundError(f"sfincs_exe not found: {sfincs_exe}")
            cmd = [str(sfincs_exe)]
        elif self.params.vm is not None:
            vm = self.params.vm
            docker_tag = self.params.docker_tag
            if vm == "docker":
                cmd = [
                    "docker",
                    "run",
                    f"-v{model_root}://data",
                    f"deltares/sfincs-cpu:{docker_tag}",
                ]
            elif vm == "singularity":
                cmd = [
                    "singularity",
                    "run",
                    f"-B{model_root}:/data",
                    "--nv",
                    f"docker://deltares/sfincs-cpu:{docker_tag}",
                ]
        else:
            if platform.system() == "Windows":
                raise ValueError("sfince_exe must be specified for Windows")
            else:
                raise ValueError("vm must be specified for Linux or macOS")

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
        if self.params.vm is not None and return_code == 127:
            raise RuntimeError(
                f"{vm} not found. Make sure it is installed, running and added to PATH."
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
