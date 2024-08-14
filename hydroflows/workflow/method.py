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
from typing import Any, ClassVar, Dict, Generator, List, Optional, Tuple, cast

from hydroflows.workflow.method_parameters import Parameters

__all__ = ["Method"]


class Method(ABC):
    """Base method for all methods.

    The method class defines the structure of a method in a HydroFlow workflow.
    It should have a name, input, output and params, and implement a run and __init__ method.

    """

    # name of the method, should be replaced in subclass
    name: ClassVar[str] = "abstract_method"

    @abstractmethod
    def __init__(self) -> None:
        """Create a new method instance with input, output and params."""
        self.input: Parameters = Parameters()
        self.output: Parameters = Parameters()
        self.params: Parameters = Parameters()

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
        return f"Method({pformat(self.dict)})"

    ## DESERIALIZATION METHODS

    @property
    def kwargs(self) -> Dict[str, Any]:
        """Return the minimal set of keyword-arguments which result in the same method parametrization."""
        init_kw = inspect.signature(self.__init__).parameters
        in_kw = {k: v for k, v in self.dict["input"].items() if k in init_kw}
        out_kw = {k: v for k, v in self.dict["output"].items() if k in init_kw}
        kw = {**in_kw, **out_kw, **self.dict.get("params", {})}
        return kw

    @property
    def dict(self) -> Dict[str, Dict]:
        """Return a dictionary representation of the method input, output and params."""
        if not hasattr(self, "._dict") or not self._dict:
            self._dict = self.to_dict()
        return self._dict

    def to_dict(self, **kwargs) -> Dict:
        """Return a serialized dictionary representation of the method input, output and params."""
        _kwargs = dict(exclude_defaults=True, round_trip=True, mode="json")
        dump_kwargs = {**_kwargs, **kwargs}
        out_dict = {
            "name": self.name,
            "input": self.input.to_dict(**dump_kwargs),
            "output": self.output.to_dict(**dump_kwargs),
        }
        if hasattr(self, "params"):  # params are optional
            out_dict["params"] = self.params.model_dump(**dump_kwargs)
        return out_dict

    ## SERIALIZATION METHODS

    @classmethod
    def from_dict(
        cls,
        input: Dict,
        output: Dict,
        params: Optional[Dict] = None,
        name: Optional[str] = None,
    ) -> "Method":
        """Create a new instance from input, output and params dictionaries.

        Parameters
        ----------
        input, output : Dict
            Dictionary with input, and output parameters.
        params : Dict, optional
            Dictionary with additional parameters, by default None.
        name : str, optional
            Name of the method, by default None.
            This is required if called from the parent Method class.
        """
        # if called from the parent class, get the subclass by name
        if cls.name == "abstract_method":
            if name is None:
                raise ValueError("Cannot initiate from Method without a method name")
            cls = cls._get_subclass(name)

        # get keyword arguments of __init__ method based on its signature
        init_kw = inspect.signature(cls.__init__).parameters
        input_kwargs = {k: v for k, v in input.items() if k in init_kw}
        output_kwargs = {k: v for k, v in output.items() if k in init_kw}
        kwargs = {**input_kwargs, **output_kwargs}
        if params is not None:
            kwargs.update(params)  # always include params

        return cls(**kwargs)

    @classmethod
    def from_kwargs(cls, name: Optional[str] = None, **kwargs) -> "Method":
        """Create a new method instance from the method `name` and its initialization arguments."""
        # if called from the parent class, get the subclass by name
        if cls.name == "abstract_method":
            if name is None:
                raise ValueError("Cannot initiate from Method without a method name")
            cls = cls._get_subclass(name)

        return cls(**kwargs)

    @classmethod
    def _get_subclasses(cls) -> Generator[type["Method"], None, None]:
        for subclass in cls.__subclasses__():
            yield from subclass._get_subclasses()
            yield subclass

    @classmethod
    def _get_subclass(cls, name: str) -> type["Method"]:
        """Get a subclass by name."""
        # FIXME use entrypoints to get all subclasses
        # for now we need to import the hydroflows.methods module to 'discover' all subclasses
        from hydroflows import methods as _  # noqa: F401

        for subclass in cls._get_subclasses():
            if subclass.name == name:
                return subclass
        known_methods = [m.name for m in cls._get_subclasses()]
        raise ValueError(f"Unknown method: {name}, select from {known_methods}")

    ## TESTING METHODS

    def _test_roundtrip(self) -> None:
        """Test if the method can be serialized and deserialized."""
        kw = self.kwargs
        m = self.from_kwargs(kw)
        assert m.dict == self.dict

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


class ExpandMethod(Method, ABC):
    """Base class for methods that expand on a wildcard."""

    @abstractmethod
    def __init__(self) -> None:
        """Create a new expand method instance."""
        super().__init__()
        self.expand_refs: Dict[str, str] = {}  # wildcard key: output key
        # self.expand_output_keys: List[str] = []  # output keys with wildcards

    def _resolve_expand_values(self) -> None:
        """Resolve expand values based on expand_refs."""
        for wildcard, output_key in self.expand_refs.items():
            expand_value = cast(List, getattr(self.output, output_key))
            self._expand_values[wildcard] = expand_value

    @property
    def expand_values(self) -> Dict[str, List]:
        """Return a dict with wildcards and list of expand values."""
        if not hasattr(self, "_expand_values") or not self._expand_values:
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


class ReduceMethod(Method):
    """Base class for methods that convert input to output."""

    # @abstractmethod
    # def __init__(self) -> None:
    #     """Create a new expand method instance."""
    #     super().__init__()
    #     self.reduce_input_keys: List[str] = []  # input keys with wildcards
