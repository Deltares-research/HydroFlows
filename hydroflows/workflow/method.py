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
from typing import Any, ClassVar, Dict, Generator, List, Optional, Tuple

from hydroflows.workflow.method_parameters import Parameters

__all__ = ["Method"]


class Method(ABC):
    """Base method for all methods.

    The method class defines the structure of a method in a HydroFlow workflow.
    It should have a name, input, output and params, and implement a run and __init__ method.

    """

    # name of the method, should be replaced in subclass
    name: ClassVar[str] = "abstract_method"

    # Define the method kwargs for testing
    _test_kwargs = {}

    @abstractmethod
    def __init__(self) -> None:
        """Create a new method instance with input, output and params."""
        # NOTE: the parameter fields are specific to each method and should
        # be initialized in the method __init__  method.
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

    ## INPUT/OUTPUT/PARAMS PROPERTIES

    @property
    def input(self) -> Parameters:
        """Return the input parameters of the method."""
        if not hasattr(self, "_input"):
            raise ValueError("Input parameters not set")
        return self._input

    @input.setter
    def input(self, value: Parameters) -> None:
        """Set the input parameters of the method."""
        if not isinstance(value, Parameters):
            raise ValueError("Input should be a Parameters instance")
        self._input = value

    @property
    def output(self) -> Parameters:
        """Return the output parameters of the method."""
        if not hasattr(self, "_output"):
            raise ValueError("Output parameters not set")
        return self._output

    @output.setter
    def output(self, value: Parameters) -> None:
        """Set the output parameters of the method."""
        if not isinstance(value, Parameters):
            raise ValueError("Output should be a Parameters instance")
        self._output = value

    @property
    def params(self) -> Parameters:
        """Return the additional parameters of the method."""
        if not hasattr(self, "_params"):
            return Parameters()
        return self._params

    @params.setter
    def params(self, value: Parameters) -> None:
        """Set the additional parameters of the method."""
        if not isinstance(value, Parameters):
            raise ValueError("Params should be a Parameters instance")
        self._params = value

    ## MAGIC METHODS

    def __repr__(self) -> str:
        return f"Method(name={self.name}; parameters={pformat(self.dict)})"

    ## SERIALIZATION METHODS

    @property
    def kwargs(self) -> Dict[str, Any]:
        """Return the minimal set of keyword-arguments which result in the same method parametrization."""
        init_kw = inspect.signature(self.__init__).parameters
        in_kw = {k: v for k, v in self.input.to_dict("json").items() if k in init_kw}
        out_kw = {k: v for k, v in self.output.to_dict("json").items() if k in init_kw}
        kw = {**in_kw, **out_kw, **self.params.to_dict("json")}
        return kw

    @property
    def kwargs_with_refs(self) -> Dict[str, Any]:
        """Return the keyword-arguments with references."""
        init_kw = inspect.signature(self.__init__).parameters
        opt = dict(
            mode="json", return_refs=True, exclude_defaults=True, posix_path=True
        )
        in_kw = {k: v for k, v in self.input.to_dict(**opt).items() if k in init_kw}
        out_kw = {k: v for k, v in self.output.to_dict(**opt).items() if k in init_kw}
        params_kw = self.params.to_dict(**opt)
        kw = {**in_kw, **out_kw, **params_kw}
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
            "input": self.input.to_dict(**dump_kwargs),
            "output": self.output.to_dict(**dump_kwargs),
        }
        if hasattr(self, "_params"):  # params are optional
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
        # FIXME use entrypoints to get all subclasses
        # for now we need to import the hydroflows.methods module to 'discover' all subclasses

        from hydroflows import methods as _  # noqa: F401

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
        # parse all values to strings to test serialization
        kw = {k: str(v) for k, v in self.kwargs.items()}
        m = self.from_kwargs(self.name, **kw)
        assert m.dict == self.dict

    def _test_unique_keys(self) -> None:
        """Check if the method input, output and params keys are unique."""
        inputs = list(self.input.model_fields.keys())
        outputs = list(self.output.model_fields.keys())
        params = list(self.params.model_fields.keys())
        ukeys = set(inputs + outputs + params)
        nkeys = len(inputs) + len(outputs) + len(params)
        # check for unique keys
        if len(ukeys) != nkeys:
            raise ValueError("Keys of input, output and params should all be unique")

    def _test_method_kwargs(self) -> None:
        """Test if all method __init__ arguments are in input, output or params."""
        init_kw = inspect.signature(self.__init__).parameters
        # skip
        in_kw = self.input.model_fields.keys()
        out_kw = self.output.model_fields.keys()
        params_kw = self.params.model_fields.keys()
        all_kw = list(in_kw) + list(out_kw) + list(params_kw)
        for k in init_kw:
            # skip self, *args, **kwargs
            if k == "self" or init_kw[k].kind in (
                inspect.Parameter.VAR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL,
            ):
                continue
            if k not in all_kw:
                raise ValueError(
                    f"Method __init__ argument {k} not in input, output or params"
                )

    ## RUN METHODS

    def dryrun(self, missing_file_error: bool = False) -> None:
        """Run method with dummy outputs."""
        self.check_input_output_paths(missing_file_error=missing_file_error)
        # write output files
        for _, path in self._output_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write("")

    def run_with_checks(self, check_output: bool = True) -> None:
        """Run the method with input/output checks."""
        self.check_input_output_paths()
        self.run()
        if check_output:
            self.check_output_exists()

    def check_input_output_paths(self, missing_file_error: bool = True) -> None:
        """Check if input exists and output parent directory exists."""
        for key, value in self.input.model_dump().items():
            if isinstance(value, Path):
                msg = f"Input file {self.name}.input.{key} not found: {value}"
                if not value.is_file():
                    if not missing_file_error:  # create dummy file
                        print(f"WARNING: {msg}")
                        value.parent.mkdir(parents=True, exist_ok=True)
                        with open(value, "w") as f:
                            f.write("")
                    else:
                        raise FileNotFoundError(msg)
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
        # NOTE: see init of super method for requirements
        # in addition call the set_expand_wildcard method
        # self.set_expand_wildcard(wildcard, values)

    def set_expand_wildcard(self, wildcard: str, values: List[str]) -> None:
        """Set wildcard key and values.

        Parameters
        ----------
        wildcard : str
            The wildcard key.
        values : List[str]
            The list of expand values for the wildcard.
        """
        if not hasattr(self, "_expand_wildcards"):
            self._expand_wildcards: Dict[str, List] = {}
        self._expand_wildcards[wildcard] = values

    @property
    def expand_wildcards(self) -> Dict[str, List[str]]:
        """Return a dict with a list of expand values per wildcard key."""
        if not hasattr(self, "_expand_wildcards"):
            return {}
        return self._expand_wildcards

    @property
    def _output_paths(self) -> List[Tuple[str, Path]]:
        """Return a list of output key-path tuples."""
        paths = []
        for key, value in self.output.model_dump().items():
            if not isinstance(value, Path):
                continue
            for wc, vlist in self.expand_wildcards.items():
                if "{" + wc + "}" in str(value):
                    for v in vlist:
                        path = Path(str(value).format(**{wc: v}))
                        paths.append((key, path))
                else:
                    paths.append((key, value))
        return paths


class ReduceMethod(Method):
    """Base class for methods that reduce multiple inputs to one output."""

    # NOTE: for now this class merely serves to flag a a reduce method
    # it may be extended in the future to include specific reduce logic or methods
