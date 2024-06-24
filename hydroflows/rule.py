"""
HydroFlows Rule class.

Defines the relationship between input and output taking care of expansions as
forwarded from the Workflow class. Rule is agnostic across all Methods and so
requires a Method class as input.

"""

import weakref
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Tuple, Type, cast

from pydantic import BaseModel

from hydroflows.method import Method

if TYPE_CHECKING:
    from hydroflows.workflow import Workflow

__all__ = ["Rule"]

FMT = ["snakemake"]


# TODO can this also be a pydantic model?
class Rule:
    """Rule class."""

    def __init__(
        self,
        method_name: str,
        kwargs: Dict,
        workflow: "Workflow",
    ) -> None:
        """Create a rule instance.

        Parameters
        ----------
        method_name : str
            The name of the method to use in the rule.
        kwargs : Dict
            The keyword arguments to pass to the method.
        workflow : Workflow
            The workflow instance to which the rule belongs.
        """
        self.name: str = method_name

        # add weak reference to workflow to avoid circular references
        self._workflow_ref = weakref.ref(workflow)

        # get Method subclass based on method name
        self._method_class: Type[Method] = Method._get_subclass(method_name)
        # TODO add params with $config reference from Method class to kwargs
        # default values should be add to the config basemodel
        # this way we can enforce global defaults for all methods without having to
        # specify them in the workflow files
        self._kwargs = kwargs.copy()
        self._resolved_kwargs: Dict = self._resolve_kwargs(kwargs.copy())
        self.method: Method = self._method_class(**self._resolved_kwargs)

        self._wildcards: Dict = self._detect_wildcards()

    def __repr__(self) -> str:
        """Return the representation of the rule."""
        return f"Rule(name={self.name}, runs={self.runs}, wildcards={self.wildcards})"

    @property
    def workflow(self) -> "Workflow":
        """Return the workflow."""
        return self._workflow_ref()

    @property
    def wildcards(self) -> List[str]:
        """Return the wildcards that are used to explode the rule."""
        # these are the wildcards that are used in both input/params and output
        wc_in_params = set(self._wildcards["input"] + self._wildcards["params"])
        wc_out = set(self._wildcards["output"])
        return list(wc_in_params & wc_out)

    @property
    def runs(self) -> int:
        """Return the number of required method runs."""
        return len(self._wildcard_product())

    def to_dict(self) -> Dict:
        """Return the method as a dictionary."""
        return {
            "name": self.name,
            "runs": self.runs,
            "wildcards": self.wildcards,
            "input": self.input(),
            "output": self.output(),
            "params": self.params(exclude_defaults=True),
        }

    def input(
        self, filter_types: Tuple[Type] = None, filter_keys: List = None, **kwargs
    ) -> Dict:
        """Return the input of the rule."""
        kwargs = {"exclude_none": True, **kwargs}
        input = self.method.input.model_dump(**kwargs)
        if filter_types is not None:
            input = {k: v for k, v in input.items() if isinstance(v, filter_types)}
        if filter_keys is not None:
            input = {k: v for k, v in input.items() if k in filter_keys}
        return input

    def output(
        self, filter_types: Tuple[Type] = None, filter_keys: List = None, **kwargs
    ) -> Dict:
        """Return the output of the rule."""
        kwargs = {"exclude_none": True, **kwargs}
        output = self.method.output.model_dump(**kwargs)
        if filter_types is not None:
            output = {k: v for k, v in output.items() if isinstance(v, filter_types)}
        if filter_keys is not None:
            output = {k: v for k, v in output.items() if k in filter_keys}
        return output

    def params(self, filter_keys: List = None, **kwargs) -> Dict:
        """Return the params of the rule."""
        if not hasattr(self.method, "params"):
            return {}
        kwargs = {"exclude_none": True, **kwargs}
        params = self.method.params.model_dump(**kwargs)
        if filter_keys is not None:
            params = {k: v for k, v in params.items() if k in filter_keys}
        return params

    def _resolve_kwargs(self, kwargs: Dict) -> Dict:
        """Resolve the kwargs."""
        for key, value in kwargs.items():
            if isinstance(value, str) and value.startswith("$"):
                kwargs[key] = self.workflow._resolve_references(value)
        return kwargs

    def _detect_wildcards(self) -> List[str]:
        """Detect wildcards in the rule based on workflow wildcard names."""
        wildcards = {"input": [], "output": [], "params": []}
        # check for known wildcards in input and output
        for key in wildcards.keys():
            for value in getattr(self, key)().values():
                if not isinstance(value, (str, Path)):
                    continue
                value = str(value)
                for wc in self.workflow.wildcards.names:
                    if "{" + str(wc) + "}" in value and wc not in wildcards[key]:
                        wildcards[key].append(wc)
        return wildcards

    def explode_kwargs(self) -> List[Dict]:
        """Explode the kwargs over all output wildcards."""
        all_kwargs = []
        # for now assume product of all wildcards
        for wc in self._wildcard_product():
            kwargs = self._resolved_kwargs.copy()
            for key, val in kwargs.items():
                if isinstance(val, (str, Path)):
                    kwargs[key] = str(val).format(**dict(zip(self.wildcards, wc)))
            all_kwargs.append(kwargs)
        return all_kwargs

    def _wildcard_product(self) -> List[Tuple]:
        """Return the product of all wildcard values."""
        # only explode if there are wildcards on the output
        wc_values = [
            self.workflow.wildcards.get_wildcard(wc).values for wc in self.wildcards
        ]
        # drop None from list of values; this occurs when the workflow is not fully initialized yet
        wc_values = [v for v in wc_values if v is not None]
        return list(product(*wc_values))

    def run(self) -> None:
        """Run the rule."""
        all_kwargs = self.explode_kwargs()
        n = len(all_kwargs)
        for i, kwargs in enumerate(all_kwargs):
            print(f"Running method {self.name}; instance ({i+1}/{n}) ...")
            self._method_class(**kwargs).run()

    def to_str(self, fmt: str = "snakemake") -> str:
        """Return the rule as a string."""
        match fmt:
            case "snakemake":
                return self._to_snakemake()
            case _:
                raise ValueError(f"Format {fmt} not supported.")

    def _to_snakemake(self) -> str:
        """Return the rule as a snakemake rule."""
        snake = f"rule {self.name}:\n"
        # parse input; paths only
        input = self.input(mode="python", filter_types=Path)
        snake += "    input:\n"
        for key, value in input.items():
            value = self._parse_snake_key_value(key, value, "input")
            snake += f"        {key}={value},\n"
        # parse params; only if non-default and key not in kwargs
        params = self.params(
            mode="json", exclude_defaults=True, filter_keys=list(self._kwargs.keys())
        )
        if params:
            snake += "    params:\n"
            for key, value in params.items():
                value = self._parse_snake_key_value(key, value, "params")
                snake += f"        {key}={value},\n"
        # parse output; paths only
        output = self.output(mode="python", filter_types=Path)
        snake += "    output:\n"
        for key, value in output.items():
            value = self._parse_snake_key_value(key, value, "output")
            snake += f"        {key}={value},\n"
        # shell command
        snake += "    shell:\n"
        snake += '        """\n'
        snake += f"        hydroflows method {self.method.name} \\\n"
        for key in self._resolved_kwargs.keys():
            value = self._parse_snake_shell_key_value(key)
            snake += f"        {key}={value} \\\n"
        snake += '        """\n'
        return snake

    def _parse_snake_key_value(self, key, val, comp) -> str:
        """Expand the wildcards in a string."""
        # replace val with references to config or other rules
        kwargs = self._kwargs
        if key in kwargs and kwargs[key].startswith("$"):
            if kwargs[key].startswith("$config"):
                # resolve to python dict-like access
                dict_keys = kwargs[key].split(".")[1:]
                v = 'config["' + '"]["'.join(dict_keys) + '"]'
            elif kwargs[key].startswith("$rules"):
                v = f"{kwargs[key][1:]}"
        else:
            # check in wildcard in value which should be expanded
            # wildcards are in the form {wildcard_name}
            expand_kwargs = []
            for wc in self._wildcards[comp]:
                if "{" + wc + "}" in str(val):
                    # NOTE wildcard values will be added by the workflow in upper case
                    expand_kwargs.append(f"{wc}={wc.upper()}")
            if expand_kwargs:
                # NOTE we assume product of all wildcards, this could be extended to also use zip
                expand_kwargs_str = ", ".join(expand_kwargs)
                v = f'expand("{val}", {expand_kwargs_str})'
            else:
                # no references or wildcards, just add the value with quotes
                v = f'"{val}"'
        return v

    def _parse_snake_shell_key_value(self, key) -> str:
        """Parse the key value pair for the shell command."""
        # check if key is in input, output or params
        for c in ["input", "output", "params"]:
            comp = cast(BaseModel, getattr(self.method, c))
            if key in comp.model_fields:
                value = f"{c}.{key}"
                return '"{' + value + '}"'
        raise ValueError(f"Key {key} not found in input, output or params.")
