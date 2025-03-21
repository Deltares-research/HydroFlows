""""Dummy methods for testing and user documentation."""
from pathlib import Path

from hydroflows._typing import ListOfInt
from hydroflows.workflow import ExpandMethod, Parameters


class PrepareDummyEventsInput(Parameters):
    """Input files for the PrepareDummyEvents method."""

    timeseries_csv: Path
    """Input timeseirse csv file"""


class PrepareDummyEventsOutput(Parameters):
    """Output files for the PrepareDummyEvents method."""

    event_csv: Path
    """Event csv file"""

    event_set_yaml: Path
    """Overview of all events"""


class PrepareDummyEventsParams(Parameters):
    """Parameters for the PrepareDummyEvents method."""

    output_dir: Path
    """Output directory"""

    index_col: int = 0
    """Index column"""

    wildcard: str = "return_period"
    """Wildcard for expanding"""

    rps: ListOfInt = [1, 10, 100, 1000]
    """Return periods [years]"""


class PrepareDummyEvents(ExpandMethod):
    """Prepare events for some model.

    Parameters
    ----------
    timeseries_csv : Path
        Input timeseries csv file
    output_dir : Path
        Output directory
    rps : List[int]
        Return periods [years].
        This is used to expand the outputs and create a file for each return period.
    wildcard : str
        Wildcard name used to expand the outputs over `rps`.
    **params
        Additional parameters for the method, see :class:`~hydroflows.methods.dummy.PrepareDummyEventsParams`.
    """

    input: PrepareDummyEventsInput
    output: PrepareDummyEventsOutput
    params: PrepareDummyEventsParams
    name = "prepare_dummy_events"

    _test_kwargs = {
        "timeseries_csv": "data.csv",
        "output_dir": "output",
    }

    def __init__(
        self,
        timeseries_csv: Path,
        output_dir: Path,
        rps: list[int] = [1, 10, 100, 1000],  # noqa: B006
        wildcard: str = "return_period",
        **params,
    ):
        self.input = PrepareDummyEventsInput(timeseries_csv=timeseries_csv)
        self.params = PrepareDummyEventsParams(
            output_dir=output_dir, rps=rps, wildcard=wildcard, **params
        )
        wc = "{" + self.params.wildcard + "}"
        self.output = PrepareDummyEventsOutput(
            event_csv=self.params.output_dir / f"event_rp{wc}.csv",
            event_set_yaml=self.params.output_dir / "event_set.yml",
        )

        self.set_expand_wildcard(
            self.params.wildcard, [f"{rp:04d}" for rp in self.params.rps]
        )

    def _run(self):
        # Read the data
        # Save the outputs
        for rp in self.params.rps:
            # Do some processing per return period
            # Save the event
            output = self.get_output_for_wildcards({self.params.wildcard: f"{rp:04d}"})
            output["event_csv"].touch()
        # Save the event set
        self.output.event_set_yaml.touch()
