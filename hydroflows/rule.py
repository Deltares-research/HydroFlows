"""
HydroFlows Rule class.

Defines the relationship between input and output taking care of expansions as
forwarded from the Workflow class. Rule is agnostic across all Methods and so
requires a Method class as input.

"""

import weakref
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Tuple, Type

from tqdm.contrib.concurrent import thread_map

from hydroflows.methods.method import ExpandMethod, Method

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
        repr_dict = {"name": self.name, "runs": self.n_runs}
        if self.wildcards:
            repr_dict["wildcards"] = self.wildcards
        if isinstance(self.method, ExpandMethod):
            repr_dict["expand"] = list(self.method.expand_values.keys())
        repr_str = ", ".join([f"{k}={v}" for k, v in repr_dict.items()])
        return f"Rule({repr_str})"

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
    def n_runs(self) -> int:
        """Return the number of required method runs."""
        return len(self._wildcard_product())

    def to_dict(self) -> Dict:
        """Return the method as a dictionary."""
        out_dict = {
            "name": self.name,
            "runs": self.n_runs,
            "input": self.input(),
            "output": self.output(),
            "params": self.params(exclude_defaults=True),
        }
        if isinstance(self.method, ExpandMethod):
            out_dict["expand"] = list(self.method.expand_values.keys())
        if self.wildcards:
            out_dict["wildcards"] = self.wildcards
        return out_dict

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
        # add expand wildcards to workflow wildcards
        if isinstance(self.method, ExpandMethod):
            for key, val in self.method.expand_values.items():
                self.workflow.wildcards.set(key, val)

        # check for wildcards in input and output
        wildcards = {"input": [], "output": [], "params": []}
        for key in wildcards.keys():
            for value in getattr(self, key)().values():
                if not isinstance(value, (str, Path)):
                    continue
                value = str(value)
                for wc in self.workflow.wildcards.names:
                    if "{" + str(wc) + "}" in value and wc not in wildcards[key]:
                        wildcards[key].append(wc)

        # make sure wildcards in output which are not in input match expand_refs
        if isinstance(self.method, ExpandMethod):
            expand_wc = list(set(wildcards["output"]) - set(wildcards["input"]))
            if expand_wc != list(set(self.method.expand_values.keys())):
                raise ValueError(
                    f"Wildcards in output {expand_wc} do not match method {self.name} "
                    f"expand_refs: {self.method.expand_refs.keys()}"
                )

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
        wc_values = [self.workflow.wildcards.get(wc) for wc in self.wildcards]
        # drop None from list of values; this occurs when the workflow is not fully initialized yet
        wc_values = [v for v in wc_values if v is not None]
        return list(product(*wc_values))

    def run(self, max_workers=None) -> None:
        """Run the rule."""
        tqdm_kwargs = {}
        if max_workers is not None:
            tqdm_kwargs.update(max_workers=max_workers)

        all_kwargs = self.explode_kwargs()
        if len(all_kwargs) == 1 or max_workers == 1:
            self._run_method_instance(all_kwargs[0])
        else:
            thread_map(self._run_method_instance, all_kwargs, **tqdm_kwargs)

    def _run_method_instance(self, kwargs: Dict) -> None:
        """Run a method instance with the given kwargs."""
        m = self._method_class(**kwargs)
        m.run_with_checks()
