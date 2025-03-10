""""Dummy methods for testing and user documentation."""
from pathlib import Path
from typing import Literal

from hydroflows.workflow import Method, Parameters


class RunDummyEventInput(Parameters):
    """Input files for the RunDummyEvent method."""

    event_csv: Path
    """Event csv file"""

    settings_toml: Path
    """Model sttings file"""

    model_exe: Path | None = None
    """Model executable, required if run_method is 'exe'"""


class RunDummyEventOutput(Parameters):
    """Output files for the RunDummyEvent method."""

    model_out_nc: Path
    """Model output netcdf file"""


class RunDummyEventParams(Parameters):
    """Parameters for the RunDummyEvent method."""

    run_method: Literal["exe", "docker"] = "exe"
    """How to run the model"""

    output_dir: Path
    """The output directory"""

    event_name: str
    """The event name"""


class RunDummyEvent(Method):
    """Run an event with some model."""

    input: RunDummyEventInput
    output: RunDummyEventOutput
    params: RunDummyEventParams
    name = "run_dummy_event"

    _test_kwargs = {
        "event_csv": "event.csv",
        "settings_toml": "settings.toml",
        "output_dir": "output",
        "run_method": "docker",
    }

    def __init__(
        self,
        event_csv: Path,
        settings_toml: Path,
        output_dir: Path,
        event_name: str | None = None,
        model_exe: Path | None = None,
        **params,
    ):
        """Create a RunDummyEvent instance.

        Parameters
        ----------
        event_csv : Path
            Event csv file
        settings_toml : Path
            Model settings file
        output_dir : Path
            Output directory
        event_name : str, optional
            The event name, by default None
        model_exe : Path, optional
            Model executable, required if run_method is 'exe', by default None
        **params
            Additional parameters to pass to the RunDummyEvent Params instance.
            See :py:class:`~hydroflows.methods.dummy.RunDummyEventParams`.
        """
        self.input = RunDummyEventInput(
            event_csv=event_csv, settings_toml=settings_toml, model_exe=model_exe
        )
        if event_name is None:
            event_name = self.input.event_csv.stem
        self.params = RunDummyEventParams(
            output_dir=output_dir, event_name=event_name, **params
        )
        if self.params.run_method == "exe" and model_exe is None:
            raise ValueError("Model executable is required for run_method 'exe'")
        self.output = RunDummyEventOutput(
            model_out_nc=self.params.output_dir / f"event_{event_name}_result.nc"
        )

    def _run(self):
        # Dummy run model and save output
        self.output.model_out_nc.touch()
