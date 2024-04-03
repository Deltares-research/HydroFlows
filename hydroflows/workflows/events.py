"""Defines the Event class which is a breakpoint between workflows."""


from pathlib import Path
from typing import Any, List, Literal, Optional, Union

import yaml
from pydantic import (
    BaseModel,
    DirectoryPath,
    FilePath,
    field_validator,
    model_validator,
)

__all__ = ['EventCatalog']


class Driver(BaseModel):
    """A driver for the event."""

    type: Literal['water_level', 'discharge', 'rainfall']
    path: Path


class Event(BaseModel):
    """A model event."""

    name: str
    drivers: List[Driver]
    probability: Optional[float] = None

    @field_validator('drivers', mode='before')
    @classmethod
    def _set_drivers(cls, value: Any) -> List[Driver]:
        if isinstance(value, list):
            return [Driver(**driver) for driver in value]
        return value


class EventCatalog(BaseModel):
    """A dictionary of event configurations."""

    version: str = 'v0.1'
    root: Optional[DirectoryPath] = None
    events: List[Event]

    @field_validator('events', mode='before')
    @classmethod
    def _set_events(cls, value: Any) -> List[Event]:
        if isinstance(value, list):
            return [Event(**event) for event in value]
        return value

    @model_validator(mode='after')
    def _check_paths(self) -> 'EventCatalog':
        root = self.root or Path.cwd()
        for event in self.events:
            for driver in event.drivers:
                if not driver.path.is_absolute() and (root / driver.path).exists():
                    driver.path = root / driver.path
                if not driver.path.exists():
                    err = f"Driver {driver.path} for event {event.name} does not exist."
                    raise IOError(err)
        return self


    @classmethod
    def from_yaml(cls, path: FilePath) -> 'EventCatalog':
        """Create an EventCatalog from a YAML file."""
        with open(path, 'r') as file:
            yml_dict = yaml.safe_load(file)
        if 'root' not in yml_dict:
            yml_dict['root'] = Path(path).parent
        return cls(**yml_dict)

    def to_dict(self) -> dict:
        """Return the EventCatalog as a dictionary."""
        return self.model_dump(mode='json', round_trip=True, exclude_none=True)


    def to_yaml(self, path: FilePath) -> None:
        """Write the EventCatalog to a YAML file."""
        with open(path, 'w') as file:
            yaml.safe_dump(self.to_dict(), file, sort_keys=False)

    def get_event(self, name: str) -> Optional[Event]:
        """Get an event by name."""
        for event in self.events:
            if event.name == name:
                return event
        return None

    def get_event_dict(self, name: str) -> dict:
        """Get an event by name as a dictionary."""
        event = self.get_event(name)
        if event is not None:
            return event.model_dump(mode='json', round_trip=True, exclude_none=True)
        return {}

    @property
    def event_names(self) -> list[str]:
        """Return a list of event names."""
        return [event.name for event in self.events]

    def add_event(self, event: Union[Event, dict]) -> None:
        """Add an event."""
        if isinstance(event, dict):
            event = Event(**event)
        self.events.append(event)
