"""Dummy methods submodule for testing and user documentation."""

from hydroflows.methods.dummy.combine_dummy_events import CombineDummyEvents
from hydroflows.methods.dummy.postprocess_dummy_event import PostprocessDummyEvent
from hydroflows.methods.dummy.prepare_dummy_events import PrepareDummyEvents
from hydroflows.methods.dummy.run_dummy_event import RunDummyEvent

__all__ = [
    "PrepareDummyEvents",
    "RunDummyEvent",
    "CombineDummyEvents",
    "PostprocessDummyEvent",
]
