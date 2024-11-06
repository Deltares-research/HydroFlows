"""FIAT run rule/ submodule."""

import subprocess
from pathlib import Path

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`FIATRun` method.
    """

    # fiat_hazard: Path
    # """The path to the FIAT hazard or risk (NetCDF) file."""

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file from the
    FIAT model that needs to be run."""


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`FIATRun` method.
    """

    fiat_out: Path
    """The resulting file from the fiat calculations."""


class Params(Parameters):
    """Parameters.

    Instances of this class are used in the :py:class:`FIATRun`
    method to define the required settings.
    """

    fiat_bin: Path
    """The path to the FIAT executable."""

    threads: int = 1
    """The number of the threads to be used."""


class FIATRun(Method):
    """Rule for running a FIAT model.

    This class utilizes the :py:class:`Params <hydroflows.methods.fiat.fiat_run.Params>`,
    :py:class:`Input <hydroflows.methods.fiat.fiat_run.Input>`, and
    :py:class:`Output <hydroflows.methods.fiat.fiat_run.Output>` classes to
    run an existing FIAT model.
    """

    name: str = "fiat_run"

    _test_kwargs = {
        "fiat_cfg": Path("fiat.toml"),
        "fiat_bin": Path("fiat.exe"),
    }

    def __init__(self, fiat_cfg: Path, fiat_bin: Path, **params):
        """Create and validate a fiat_run instance.

        Parameters
        ----------
        fiat_cfg : Path
            Path to the FIAT config file.
        fiat_bin : Path
            Path to the FIAT executable
        **params
            Additional parameters to pass to the FIATRun instance.
            See :py:class:`fiat_run Params <hydroflows.methods.fiat.fiat_run.Params>`.

        See Also
        --------
        :py:class:`fiat_run Input <hydroflows.methods.fiat.fiat_run.Input>`
        :py:class:`fiat_run Output <hydroflows.methods.fiat.fiat_run.Output>`
        :py:class:`fiat_run Params <hydroflows.methods.fiat.fiat_run.Params>`
        """
        self.params: Params = Params(fiat_bin=fiat_bin, **params)
        self.input: Input = Input(fiat_cfg=fiat_cfg)
        self.output: Output = Output(
            fiat_out=self.input.fiat_cfg.parent
            / "output"
            / self.input.fiat_cfg.stem.split("_", 1)[1]
            / "spatial.gpkg"
        )

    def run(self):
        """Run the FIATRun method."""
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
