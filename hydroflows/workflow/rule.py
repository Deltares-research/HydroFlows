"""
HydroFlows Rule class.

Defines the relationship between input and output taking care of expansions as
forwarded from the Workflow class. Rule is agnostic across all Methods and so
requires a Method class as input.

"""

import weakref
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, Union, cast

from tqdm.contrib.concurrent import thread_map

from hydroflows.workflow.method import ExpandMethod, Method
from hydroflows.workflow.method_parameters import Parameters

if TYPE_CHECKING:
    from hydroflows.workflow.workflow import Workflow

__all__ = ["Rule"]

FMT = ["snakemake"]


class Rule:
    """Rule class.

    This class
    - resolves references in kwargs
    - initializes a method instance based on the method name and kwargs
    - detects wildcards in input, output and params (TODO: move to method)
    """

    def __init__(
        self,
        method: Method,
        workflow: "Workflow",
        rule_id: Optional[str] = None,
    ) -> None:
        """Create a rule instance.

        Parameters
        ----------
        method : Method
            The method instance to run.
        workflow : Workflow
            The workflow instance to which the rule belongs.
        rule_id : str, optional
            The rule id, by default None (method name).
        """
        if not isinstance(method, Method):
            raise ValueError("Method should be an instance of Method.")
        self.method: Method = method

        # add weak reference to workflow to avoid circular references
        self._workflow_ref = weakref.ref(workflow)

        # set rule id which defaults to method name
        if rule_id is None:
            rule_id = method.name
        self.rule_id: str = str(rule_id)

        # detect wildcards
        self._all_wildcards_fields: List[str] = []

        self._detect_wildcards()

    def __repr__(self) -> str:
        """Return the representation of the rule."""
        repr_dict = {"id": self.rule_id, "runs": self.n_runs}
        # if self.wildcards:
        #     repr_dict["wildcards"] = self.wildcards
        # if isinstance(self.method, ExpandMethod):
        #     repr_dict["expand"] = list(self.method.expand_values.keys())
        repr_str = ", ".join([f"{k}={v}" for k, v in repr_dict.items()])
        return f"Rule({repr_str})"

    @property
    def workflow(self) -> "Workflow":
        """Return the workflow."""
        return self._workflow_ref()

    @property
    def n_runs(self) -> int:
        """Return the number of required method runs."""
        return len(self._wildcard_product()[1])

    @property
    def wildcards(self) -> Dict[str, List]:
        """Return the wildcards of the rule.

        Wildcards are saved for three categories, based on whether these
        "expand" (1:n), "reduce" (n:1) and "explode" (n:n) the method.
        """
        if not hasattr(self, "_wildcards") or not self._wildcards:
            self._wildcards = self._detect_wildcards()
        return self._wildcards

    # def to_dict(self) -> Dict:
    #     """Return the method as a dictionary."""
    #     out_dict = {
    #         "name": self.name,
    #         "runs": self.n_runs,
    #         "input": self.input(),
    #         "output": self.output(),
    #         "params": self.params(exclude_defaults=True),
    #     }
    #     if isinstance(self.method, ExpandMethod):
    #         out_dict["expand"] = list(self.method.expand_values.keys())
    #     if self.wildcards:
    #         out_dict["wildcards"] = self.wildcards
    #     return out_dict

    @property
    def input(self) -> Parameters:
        """Return the input parameters of the rule."""
        return self.method.input

    @property
    def output(self) -> Parameters:
        """Return the output parameters of the rule."""
        return self.method.output

    @property
    def params(self) -> Parameters:
        """Return the params parameters of the rule."""
        return cast(Parameters, self.method.params)

    ## WILDCARD METHODS

    def _detect_wildcards(self) -> Dict[str, List]:
        """Detect wildcards based on known workflow wildcard names.

        This method should be called from the Workflow passing the known wildcards.
        """
        # add expand wildcards to workflow wildcards
        if isinstance(self.method, ExpandMethod):
            for wc, val in self.method.expand_values.items():
                self.workflow.wildcards.set(wc, val)

        known_wildcards = self.workflow.wildcards.names
        # check for wildcards in input and output
        wildcards: Dict[str, List] = {"input": [], "output": [], "params": []}
        wildcard_fields = []
        for sec in wildcards.keys():
            for field, value in self.method.dict[sec].items():
                if not isinstance(value, (str, Path)):
                    continue
                value = str(value)
                for wc in known_wildcards:
                    if "{" + str(wc) + "}" in value:
                        if wc not in wildcards[sec]:
                            wildcards[sec].append(wc)
                        wildcard_fields.append(field)
        self._all_wildcards_fields = wildcard_fields

        # these are the wildcards that are used in both input/params and output
        wc_in_params = set(wildcards["input"] + wildcards["params"])
        wc_out = set(wildcards["output"])

        # set the wildcards
        return {
            "explode": list(wc_in_params & wc_out),
            "expand": list(wc_out - wc_in_params),
            "reduce": list(wc_in_params - wc_out),
        }

    def explode_kwargs(self) -> List[Dict]:
        """Explode the kwargs over all output wildcards."""
        all_kwargs = []
        # for now assume product of all wildcards
        wc_keys, wc_values = self._wildcard_product()
        for wc_val in wc_values:
            kwargs = self.method.kwargs.copy()
            for key in self._all_wildcards_fields:
                kwargs[key] = str(kwargs[key]).format(**dict(zip(wc_keys, wc_val)))
            all_kwargs.append(kwargs)
        return all_kwargs

    def _wildcard_product(self) -> Tuple[List[str], List[Tuple]]:
        """Return the product of all wildcard values."""
        # only explode if there are wildcards on the output
        wildcards = self.wildcards["explode"]
        wc_values = [self.workflow.wildcards.get(wc) for wc in wildcards]
        # drop None from list of values; this occurs when the workflow is not fully initialized yet
        wc_values = [v for v in wc_values if v is not None]
        return wildcards, list(product(*wc_values))

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


class Rules:
    """Rules class.

    Rules are dynamically stored as attributes of the Rules class for easy access.
    The order of rules is stored in the rules attribute.
    """

    def __init__(self, rules: Optional[List[Rule]] = None) -> None:
        self.rules: List[str] = []
        """Ordered list of rule IDs."""

        if rules:
            for rule in rules:
                self.set(rule)

    def __repr__(self) -> str:
        """Return the representation of the rules."""
        return f"Rules({self.rules})"

    def set_rule(self, rule: Rule) -> None:
        """Set rule."""
        rule_id = rule.rule_id
        self.__setitem__(rule_id, rule)

    def get_rule(self, rule_id: str) -> Rule:
        """Get rule based on rule_id."""
        return self.__getitem__(rule_id)

    # method for getting a rule using numerical index,
    # i.e. rules[0] and rules['rule_id'] are both valid
    def __getitem__(self, key: Union[int, str]) -> Rule:
        if isinstance(key, int) and key < len(self.rules):
            key = self.rules[key]
        if key not in self.rules:
            raise ValueError(f"Rule {key} not found.")
        rule: Rule = getattr(self, key)
        return rule

    def __setitem__(self, key: str, rule: Rule) -> None:
        if not isinstance(rule, Rule):
            raise ValueError("Rule should be an instance of Rule.")
        if hasattr(self, key):
            raise ValueError(f"Rule {key} already exists.")
        setattr(self, key, rule)
        self.rules.append(key)

    def __iter__(self) -> Iterator[Rule]:
        return iter([self[rule_id] for rule_id in self.rules])

    def __next__(self) -> Rule:
        return next(self)

    def __len__(self) -> int:
        return len(self.rules)
