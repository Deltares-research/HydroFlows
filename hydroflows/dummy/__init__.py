"""Dummy methods submodule for testing and user documentation."""

from hydroflows.dummy.combine_dummy_events import CombineDummyEvents
from hydroflows.dummy.postprocess_dummy_event import PostprocessDummyEvent
from hydroflows.dummy.prepare_dummy_events import PrepareDummyEvents
from hydroflows.dummy.run_dummy_event import RunDummyEvent

__all__ = [
    "PrepareDummyEvents",
    "RunDummyEvent",
    "CombineDummyEvents",
    "PostprocessDummyEvent",
]
