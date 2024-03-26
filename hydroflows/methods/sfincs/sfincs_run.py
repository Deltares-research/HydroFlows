"""SFINCS run method."""

import subprocess
import sys
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

    sfincs_exe: FilePath
    vm: Optional[Literal["docker", "singularity"]] = None
    docker_tag: str = "latest"


class SfincsRun(Method):
    """Rule for running a SFINCS model."""

    name: str = "sfincs_run"
    params: Params = Params()
    input: Input
    output: Output


def run(self) -> None:
    """Run the SFINCS model."""
    # make sure model_root is an absolute path
    model_root = self.input.sfincs_inp.parent.resolve()

    # set command to run depending on OS and VM
    if self.params.sfincs_exe is not None and sys.platform == "win32":
        sfincs_exe = self.params.sfincs_exe.resolve()
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
        if sys.platform == "win32":
            raise ValueError("sfince_exe must be specified for Windows")
        else:
            raise ValueError("vm must be specified for Linux or macOS")

    # print(f"Running SFINCS model in {model_root} with command:")
    # print(f">> {' '.join(cmd)}\n")

    # run & write log file
    with subprocess.Popen(
        cmd,
        cwd=model_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,  # get string output instead of bytes
    ) as proc:
        with open(model_root / "sfincs_log.txt", "w") as f:
            for line in proc.stdout:
                f.write(line)
            for line in proc.stderr:
                f.write(line)
        proc.wait()
        return_code = proc.returncode

    # check return code
    if vm is not None and return_code == 127:
        raise RuntimeError(
            f"{vm} not found. Make sure it is installed, running and added to PATH."
        )
    elif return_code != 0:
        raise RuntimeError(f"SFINCS run failed with return code {return_code}")

    return None
