.. currentmodule:: hydroflows.events

Event
-----
Describes an event, including forcing data, and timne range of a simulation

.. autosummary::
   :toctree: ../_generated

    Event
    Event.from_yaml
    Event.read_forcing_data
    Event.set_time_range_from_forcings
    Event.to_dict
    Event.to_yaml

EventSet
--------
Describes several events that have coherence (e.g. part of the same statistical population).

.. autosummary::
   :toctree: ../_generated

    EventSet
    EventSet.to_dict
    EventSet.to_yaml
    EventSet.get_event
    EventSet.get_event_data
    EventSet.add_event
