"""HydroFlows Method class.

A method is where the actual work of a rule happens.
It should have a name, inputs, and outputs, and optionally params.

All HydroFlow methods should inherit from this class and implement specific
validators and a run method.
"""

import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, Generator, List, Optional, Tuple

from hydroflows.utils.parsers import has_wildcards
from hydroflows.workflow.method_entrypoints import METHODS
from hydroflows.workflow.method_parameters import Parameters
from hydroflows.workflow.wildcards import resolve_wildcards

__all__ = ["Method"]

logger = logging.getLogger(__name__)


class Method(ABC):
    """Base method for all methods.

    The method class defines the structure of a method in a HydroFlow workflow.
    It should have a name, input, output and params, and implement a _run and __init__ method.
    """

    # name of the method, should be replaced in subclass
    name: ClassVar[str] = "abstract_method"

    # Define the method kwargs for testing
    _test_kwargs = {}

    @abstractmethod
    def __init__(self) -> None:
        # NOTE: the parameter fields are specific to each method and should
        # be initialized in the method __init__  method.
        self.input: Parameters = Parameters()
        # NOTE: wildcards on outputs should be defined on file parent, not the file name itself!
        self.output: Parameters = Parameters()
        self.params: Parameters = Parameters()

    ## ABSTRACT METHODS

    @abstractmethod
    def _run(self) -> None:
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
        parameters = "\n ".join([f"{k}=({getattr(self, k)})" for k in self.dict])
        method_type = self.__class__.__bases__[0].__name__
        expand = ""
        if isinstance(self, ExpandMethod):
            wcs = " ".join([f"{k}={v}" for k, v in self.expand_wildcards.items()])
            expand = f" expand_wildcards=({wcs})\n"
        return f"{method_type}(\n name={self.name}\n {parameters}\n{expand})"

    def __eq__(self, other: "Method") -> bool:
        return (
            self.__class__ == other.__class__
            and self.name == other.name
            and self.to_dict() == other.to_dict()
        )

    ## SERIALIZATION METHODS

    def to_kwargs(
        self,
        mode="json",
        exclude_defaults=True,
        posix_path=False,
        return_refs=False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return flattened keyword-arguments which result in the same method parametrization."""
        kwargs = dict(
            mode=mode, posix_path=posix_path, return_refs=return_refs, **kwargs
        )
        # get all input, output which are in the __init__ signature
        par = set(inspect.signature(self.__init__).parameters.keys())
        # Add extra optional (not defined) vars from input
        par.update(par ^ set(self.input.to_dict().keys()))
        par = list(par)
        # Get the arguments
        in_kw = self.input.to_dict(filter_keys=par, **kwargs)
        out_kw = self.output.to_dict(filter_keys=par, **kwargs)
        # get all non-default params
        params_kw = self.params.to_dict(exclude_defaults=exclude_defaults, **kwargs)
        return {**in_kw, **out_kw, **params_kw}

    def _kwargs_to_key_mapping(self) -> Dict[str, str]:
        """Return kwarg-key to input/output/params-key mapping."""
        # check if key is in input, output or params
        mapping = {}
        for key in self.to_kwargs().keys():
            for c in ["input", "output", "params"]:
                if key in self.dict.get(c, {}):
                    mapping[key] = f"{c}.{key}"
                    break
            if key not in mapping:
                raise ValueError(f"Key {key} not found in {self.name}.")
        return mapping

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
            "params": {},
        }
        if hasattr(self, "_params"):  # params are optional
            out_dict["params"] = self.params.to_dict(**dump_kwargs)
        return out_dict

    ## SERIALIZATION METHODS

    @classmethod
    def from_kwargs(cls, method_name: Optional[str] = None, **kwargs) -> "Method":
        """Create a new method instance from the method `name` and its initialization arguments."""
        # if called from the parent class, get the subclass by name
        if cls.name == "abstract_method":
            if method_name is None:
                raise ValueError("Cannot initiate from Method without a method name")
            cls = cls._get_subclass(method_name)

        return cls(**kwargs)

    @classmethod
    def _get_subclasses(cls) -> Generator[type["Method"], None, None]:
        """Get all imported subclasses of the Method class."""
        for subclass in cls.__subclasses__():
            yield from subclass._get_subclasses()
            yield subclass

    @classmethod
    def _get_subclass(cls, name: str) -> type["Method"]:
        """Get a subclass by name."""
        name = name.lower()
        for subclass in cls._get_subclasses():
            if subclass.name.lower() == name or subclass.__name__.lower() == name:
                return subclass
        # if not found, try to import the module using entry points
        return METHODS.load(name)

    ## TESTING METHODS (we keep these here such that external implementations can use them)

    def _test_roundtrip(self) -> None:
        """Test if the method can be serialized and deserialized."""
        # parse all values to strings to test serialization
        kw = self.to_kwargs(exclude_defaults=False, posix_path=True)
        kw = {k: str(v) for k, v in kw.items()}
        m = self.from_kwargs(self.name, **kw)
        if m.dict != self.dict:
            raise ValueError("Method serialization failed")

    def _test_unique_keys(self) -> None:
        """Check if the method input, output and params keys are unique."""
        inputs = list(self.input.model_fields.keys())
        outputs = list(self.output.model_fields.keys())
        params = list(self.params.model_fields.keys())
        ukeys = set(inputs + outputs + params)
        if "method_name" in ukeys:
            raise ValueError("Key 'method_name' is reserved for the method name")
        nkeys = len(inputs) + len(outputs) + len(params)
        # check for unique keys
        if len(ukeys) != nkeys:
            raise ValueError("Keys of input, output and params should all be unique")

    def test_method(self) -> None:
        """Run all tests on the method."""
        errors = []
        try:
            self._test_unique_keys()
        except Exception as e:
            errors.append(e)
        try:
            self._test_roundtrip()
        except Exception as e:
            errors.append(e)
        if errors:
            msg = "\n".join([str(e) for e in errors])
            raise ValueError(f"Method tests failed:\n{msg}")

    ## RUN METHODS

    def dryrun(
        self, input_files: List[Path], missing_file_error: bool = False
    ) -> List[Path]:
        """Run method with dummy outputs.

        Parameters
        ----------
        input_files : List[Path]
            List of input paths to check, by default None.
        missing_file_error : bool, optional
            Raise an error if a missing file is encountered, by default False.

        Returns
        -------
        List[Path]
            List of output paths.
        """
        for key, value in self.input.model_dump().items():
            if isinstance(value, Path):
                if value not in input_files and not value.is_file():
                    msg = f"Input file {self.name}.input.{key} not found: {value}"
                    if missing_file_error:
                        raise FileNotFoundError(msg)
                    else:
                        logger.warning(msg)
        # return output paths
        return [value for _, value in self._output_paths]

    def run(self, check_output: bool = True) -> None:
        """Run the method with input/output checks.

        Parameters
        ----------
        check_output : bool, optional
            Check if output files are created, by default True.
        """
        # TODO warning if wildcards on input / params
        self.check_input_output_paths()
        self._run()
        if check_output:
            self.check_output_exists()

    def check_input_output_paths(
        self,
        missing_file_error: bool = True,
    ) -> None:
        """Check if input exists and output parent directory exists.

        Parameters
        ----------
        missing_file_error : bool, optional
            Raise an error if a missing file is encountered, by default True.
        """
        for key, value in self.input.model_dump().items():
            if isinstance(value, Path):
                if has_wildcards(value):
                    raise ValueError(
                        f"The method {self.name} has unresolved wildcards in input paths. "
                        "Please create a rule to resolve these wildcards and run the rule."
                    )
                if not value.is_file():
                    msg = f"Input file {self.name}.input.{key} not found: {value}"
                    if not missing_file_error:
                        logger.warning(msg)
                    else:
                        raise FileNotFoundError(msg)
        # get all output folders
        folders = list(set([p.parent for _, p in self._output_paths]))
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

    @property
    def _output_paths(self) -> List[Tuple[str, Path]]:
        """Return a list of output key-path tuples."""
        return [
            (key, val) for key, val in self.output.to_dict(filter_types=(Path)).items()
        ]

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
    def output_expanded(self) -> Dict[str, Path | List[Path]]:
        """Output dict with wildcards in output path evaluated."""
        if not hasattr(self, "_output_expanded"):
            self._evaluate_expand_wildcards()
        return self._output_expanded

    def _evaluate_expand_wildcards(self) -> None:
        """Evaluate wildcards in output paths."""
        self._output_expanded = {}
        for key, value in self.output.to_dict(filter_types=(Path)).items():
            value = resolve_wildcards(value, self.expand_wildcards)
            self._output_expanded[key] = value

    @property
    def _output_paths(self) -> List[Tuple[str, Path]]:
        """Return a list of output key-path tuples."""
        paths = []
        for key, val in self.output_expanded.items():
            if isinstance(val, list):
                for path in val:
                    paths.append((key, path))
            else:
                paths.append((key, val))
        return paths

    def get_output_for_wildcards(self, wildcards: dict[str, str]) -> dict[str, Path]:
        """Get the output paths for a specific wildcard configuration.

        Parameters
        ----------
        wildcards : dict[str, str]
            The wildcard configuration.
            Note that the wildcard values should be single strings.

        Returns
        -------
        dict[str, Path]
            The output paths for the wildcard configuration.
        """
        # make sure all wildcard values are strings
        if not all(isinstance(v, str) for v in wildcards.values()):
            raise ValueError("All wildcard values should be strings.")
        output = {}
        for key, path in self.output.to_dict(filter_types=(Path)).items():
            output[key] = resolve_wildcards(path, wildcards)
        return output


class ReduceMethod(Method):
    """Base class for methods that reduce multiple inputs to one output."""

    # NOTE: for now this class merely serves to flag a a reduce method
    # it may be extended in the future to include specific reduce logic or methods
