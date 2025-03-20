""""Dummy methods for testing and user documentation."""
from pathlib import Path

from hydroflows._typing import ListOfPath, WildcardPath
from hydroflows.workflow import Parameters, ReduceMethod


class CombineDummyEventsInput(Parameters):
    """Input files for the CombineDummyEvents method."""

    model_out_ncs: ListOfPath | WildcardPath
    """Model output netcdf files"""


class CombineDummyEventsOutput(Parameters):
    """Output files for the CombineDummyEvents method."""

    combined_out_nc: Path
    """Combined model output netcdf file"""


class CombineDummyEventsParams(Parameters):
    """Parameters for the CombineDummyEvents method."""

    output_dir: Path | None = None
    """Output directory"""


class CombineDummyEvents(ReduceMethod):
    """Create a CombineDummyEvents instance.

    Parameters
    ----------
    model_out_ncs : List[Path] | WildcardPath
        List of model output netcdf files or a wildcard path
    output_dir : Path, optional
        The output directory, by default None
    **params
        Additional parameters to pass to the CombineDummyEvents Params instance.
        See :py:class:`~hydroflows.methods.dummy.CombineDummyEvents`
    """

    input: CombineDummyEventsInput
    output: CombineDummyEventsOutput
    params: CombineDummyEventsParams
    name = "combine_dummy_events"

    _test_kwargs = {"model_out_ncs": ["out1.nc", "out2.nc"], "output_dir": "output"}

    def __init__(
        self,
        model_out_ncs: ListOfPath | WildcardPath,
        output_dir: Path | None = None,
        **params,
    ):
        self.params = CombineDummyEventsParams(output_dir=output_dir, **params)
        self.input = CombineDummyEventsInput(model_out_ncs=model_out_ncs)
        self.output = CombineDummyEventsOutput(
            combined_out_nc=self.params.output_dir / "events_combined.nc"
        )

    def _run(self):
        # Combine the model outputs
        self.output.combined_out_nc.touch()
