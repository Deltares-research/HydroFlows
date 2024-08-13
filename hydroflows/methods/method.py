"""HydroFlows Method class.

A method is where the actual work of a rule happens.
It should have a name, inputs, and outputs, and optionally params.

All HydroFlow methods should inherit from this class and implement specific
validators and a run method.
"""

import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from pprint import pformat
from typing import ClassVar, Dict, Generator, List, Tuple, cast

from pydantic import BaseModel

__all__ = ["Method"]


class Method(ABC):
    """Base method for all methods.

    The method class defines the structure of a method in a HydroFlow workflow.
    It should have a name, input, output and params, and implement a run and __init__ method.

    """

    # name of the method, should be replaced in subclass
    name: ClassVar[str] = "abstract_method"

    def __init__(self, input: BaseModel, output: BaseModel, params: BaseModel) -> None:
        """Create a new method instance with input, output and params."""
        self.input = input
        self.output = output
        self.params = params

        # placeholder
        self.wildcards: Dict[str, List[str]] = {}
        """Wildcards detected for expanding (1:n), reducing (n:1) and exploding (n:n) the method."""

    ## ABSTRACT METHODS

    @abstractmethod
    def run(self) -> None:
        """Implement the rule logic here.

        This method is called when executing the rule.
        """
        # NOTE: this should be implemented in the specific rule
        # it can use input, output and params, e.g. self.input.file1
        # raise NotImplementedError
        pass

    ## MAGIC METHODS

    def __repr__(self) -> str:
        return f"Method({pformat(self.to_dict())})"

    ## DESERIALIZATION METHODS

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

    ## SERIALIZATION METHODS

    @classmethod
    def from_dict(cls, d: dict) -> "Method":
        """Create a new instance from a nested dictionary representation.

        The dictionary should have keys: `input`, `output` and optionally `params` and `name`.
        `name` is used to select the correct subclass if called from the parent class.
        """
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
        """Create a new method instance from the method `name` and its initialization arguments."""
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

    ## TESTING METHODS

    def _test_roundtrip(self) -> None:
        """Test if the method can be serialized and deserialized."""
        d = self.to_dict()
        m = self.from_dict(d)
        assert m.to_dict() == d

    @classmethod
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

    ## RUN METHODS

    def run_with_checks(self, check_output: bool = True) -> None:
        """Run the method with input/output checks."""
        self.check_input_output_paths()
        self.run()
        if check_output:
            self.check_output_exists()

    def check_input_output_paths(self):
        """Check if input exists and output parent directory exists."""
        for key, value in self.input.model_dump().items():
            if isinstance(value, Path):
                if not value.is_file():
                    raise FileNotFoundError(
                        f"Input file {self.name}.input.{key} not found: {value}"
                    )
        for value in self.output.model_dump().values():
            if isinstance(value, Path):
                if not value.parent.is_dir():
                    value.parent.mkdir(parents=True)

    @property
    def _output_paths(self) -> List[Tuple[str, Path]]:
        """Return a list of output key-path tuples."""
        paths = []
        for key, value in self.output.model_dump().items():
            if isinstance(value, Path):
                paths.append((key, value))
        return paths

    def check_output_exists(self):
        """Check if output files exist."""
        for key, path in self._output_paths:
            if not path.is_file():
                raise FileNotFoundError(
                    f"Output file {self.name}.output.{key} not found: {path}"
                )

    ## WILDCARD METHODS

    def _detect_wildcards(self, known_wildcards: List[str]) -> Dict[str, List]:
        """Detect wildcards based on known workflow wildcard names.

        This method should be called from the Workflow passing the known wildcards.
        """
        # check for wildcards in input and output
        wildcards = {"input": [], "output": [], "params": []}
        for key in wildcards.keys():
            for value in getattr(self, key)().values():
                if not isinstance(value, (str, Path)):
                    continue
                value = str(value)
                for wc in known_wildcards:
                    if "{" + str(wc) + "}" in value and wc not in wildcards[key]:
                        wildcards[key].append(wc)
        self._all_wildcards = wildcards

        # these are the wildcards that are used in both input/params and output
        wc_in_params = set(wildcards["input"] + wildcards["params"])
        wc_out = set(wildcards["output"])

        # set the wildcards
        self.wildcards = {
            "explode": list(wc_in_params & wc_out),
            "reduce": list(wc_out - wc_in_params),
            "expand": list(wc_in_params - wc_out),
        }


class ExpandMethod(Method):
    """Base class for methods that expand on a wildcard."""

    expand_refs: Dict[str, str] = {}  # wildcard key: output key

    def __init__(self, input: BaseModel, output: BaseModel, params: BaseModel) -> None:
        """Create and validate an ExpandMethod instance."""
        super().__init__(input, output, params)
        self._expand_values: Dict[str, List] = {}

    def _resolve_expand_values(self) -> None:
        """Resolve expand values based on expand_refs."""
        for wildcard, output_key in self.expand_refs.items():
            expand_value = cast(List, getattr(self.output, output_key))
            self._expand_values[wildcard] = expand_value

    @property
    def expand_values(self) -> Dict[str, List]:
        """Return a dict with wildcards and list of expand values."""
        if not hasattr(self, "_expand_values"):
            self._expand_values: Dict[str, List] = {}  # should be in __init__
        if not self._expand_values:
            self._resolve_expand_values()
        return self._expand_values

    @property
    def _output_paths(self) -> List[Tuple[str, Path]]:
        """Return a list of output key-path tuples."""
        paths = []
        for key, value in self.output.model_dump().items():
            if not isinstance(value, Path):
                continue
            for wc, vlist in self.expand_values.items():
                if "{" + wc + "}" in str(value):
                    for v in vlist:
                        path = Path(str(value).format(**{wc: v}))
                        paths.append((key, path))
                else:
                    paths.append((key, value))
        return paths

    # @property
    # def wildcards(self) -> List[str]:
    #     """Return a list of wildcards."""
    #     return list(self.expand_refs.keys())


class ReduceMethod(Method):
    """Base class for methods that convert input to output."""

    # reduce_refs: Dict[str, str] = {}  # wildcard key: input key

    # @property
    # def wildcards(self) -> List[str]:
    #     """Return a list of wildcards."""
    #     return list(self.reduce_refs.keys())
