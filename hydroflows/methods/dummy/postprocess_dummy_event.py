"""Dummy methods for testing and user documentation."""

from pathlib import Path

from hydroflows.workflow import Method, Parameters


class PostprocessDummyEventInput(Parameters):
    """Input files for the PostprocessDummyEvent method."""

    model_nc: Path
    """Model output netcdf file"""


class PostprocessDummyEventOutput(Parameters):
    """Output files for the PostprocessDummyEvent method."""

    postprocessed_nc: Path
    """Postprocessed netcdf file"""


class PostprocessDummyEventParams(Parameters):
    """Parameters for the PostprocessDummyEvent method."""

    output_dir: Path
    """The output directory"""

    event_name: str
    """The event name"""


class PostprocessDummyEvent(Method):
    """Postprocess a dummy event.

    Parameters
    ----------
    model_nc : Path
        Model output netcdf file
    output_dir : Path
        The output directory
    event_name : str, optional
        The event name, by default None
    """

    input: PostprocessDummyEventInput
    output: PostprocessDummyEventOutput
    params: PostprocessDummyEventParams
    name = "postprocess_dummy_event"

    _test_kwargs = {
        "model_nc": "model.nc",
        "output_dir": "output",
    }

    def __init__(
        self,
        model_nc: Path,
        output_dir: Path,
        event_name: str | None = None,
    ):
        self.input = PostprocessDummyEventInput(model_nc=model_nc)
        if event_name is None:
            event_name = self.input.model_nc.stem
        self.params = PostprocessDummyEventParams(
            output_dir=output_dir, event_name=event_name
        )
        self.output = PostprocessDummyEventOutput(
            postprocessed_nc=self.params.output_dir
            / f"event_{event_name}_postprocessed.nc"
        )

    def _run(self):
        # Run model and save output
        self.output.postprocessed_nc.touch()
