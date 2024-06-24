"""HydroFlows Method class.

A method is where the actual work of a rule happens.
It should have a name, inputs, and outputs, and optionally params.

All HydroFlow methods should inherit from this class and implement specific
validators and a run method.
"""

import inspect
from abc import ABC, abstractmethod
from pprint import pformat
from typing import ClassVar, Dict, Generator

from pydantic import BaseModel

__all__ = ["Method"]


class Method(ABC):
    """Base method for all methods. Must be extended for rule-specific tasks."""

    # name of the method, should be replaced in subclass
    name: ClassVar[str] = "abstract_method"

    def __init__(self, **params):
        # NOTE: this should be implemented in the specific rule
        # initialize input, output and params
        # relations between in- and outputs can be defined here
        # the required init kwargs should be a minimal set of parameters
        # optional parameters can be derived from other parameters or have default values
        self.input: BaseModel  # = Input(...)
        self.output: BaseModel  # = Output(...)
        self.params: BaseModel  # = Params(**params) # optional

    @abstractmethod
    def run(self) -> None:
        """Implement the rule logic here.

        This method is called when executing the rule.
        """
        # NOTE: this should be implemented in the specific rule
        # it can use input, output and params, e.g. self.input.file1
        # raise NotImplementedError
        pass

    def __repr__(self) -> str:
        return f"Method({pformat(self.to_dict())})"

    def to_dict(self, **kwargs) -> Dict:
        """Return a serialized dictionary representation of the method input, output and params."""
        _kwargs = dict(
            exclude_none=True, exclude_defaults=True, round_trip=True, mode="json"
        )
        dump_kwargs = {**_kwargs, **kwargs}
        out_dict = {
            "name": self.name,
            "input": self.input.model_dump(**dump_kwargs),
            "output": self.output.model_dump(**dump_kwargs),
        }
        if hasattr(self, "params"):  # params are optional
            out_dict["params"] = self.params.model_dump(**dump_kwargs)
        return out_dict

    @classmethod
    def from_dict(cls, d: dict) -> "Method":
        """Create a new instance from a dictionary representation."""
        # check dict keys
        if not all(k in d.keys() for k in ["input", "output"]):
            raise ValueError("Dictionary should have keys: input and output")
        name = d.get("name", cls.name)
        if not (cls.name == name or cls.name == "abstract_method"):
            raise ValueError(
                f"Method {name} cannot be initiated from class {cls.__name__} with name {cls.name}"
            )

        # get keyword arguments of __init__ method based on its signature
        init_kw = inspect.signature(cls.__init__).parameters
        for key in ["input", "output"]:
            kwargs = {k: v for k, v in d[key].items() if k in init_kw}
        kwargs.update(**d.get("params", {}))  # always include non-default params
        if cls.name == name:
            return cls(**kwargs)
        elif cls.name == "abstract_method":  # parent class
            return cls._get_subclass(name)(**kwargs)

    @classmethod
    def from_kwargs(cls, name: str, **kwargs) -> "Method":
        """Create a new instance from a name and keyword arguments."""
        if cls.name == name:
            return cls(**kwargs)
        elif cls.name == "abstract_method":  # parent class
            return cls._get_subclass(name)(**kwargs)
        else:
            raise ValueError(
                f"Method {name} cannot be initiated from class {cls.__name__} with name {cls.name}"
            )

    @classmethod
    def _get_subclasses(cls) -> Generator[type["Method"], None, None]:
        for subclass in cls.__subclasses__():
            yield from subclass._get_subclasses()
            yield subclass

    @classmethod
    def _get_subclass(cls, name: str) -> type["Method"]:
        """Get a subclass by name."""
        for subclass in cls._get_subclasses():
            if subclass.name == name:
                return subclass
        known_methods = [m.name for m in cls._get_subclasses()]
        raise ValueError(f"Unknown method: {name}, select from {known_methods}")

    def _test_roundtrip(self) -> None:
        """Test if the method can be serialized and deserialized."""
        d = self.to_dict()
        m = self.from_dict(d)
        assert m.to_dict() == d

    def _test_unique_keys(self) -> None:
        """Check if the method input, output and params keys are unique."""
        inputs = list(self.input.model_fields.keys())
        outputs = list(self.output.model_fields.keys())
        ukeys = set(inputs + outputs)
        nkeys = len(inputs) + len(outputs)
        if hasattr(self, "params"):  # params are optional
            params = list(self.params.model_fields.keys())
            ukeys = set(list(ukeys) + params)
            nkeys += len(params)
        # check for unique keys
        if len(ukeys) != nkeys:
            raise ValueError("Keys of input, output and params should all be unique")
