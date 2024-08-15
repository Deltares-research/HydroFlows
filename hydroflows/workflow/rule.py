"""HydroFlows Rule class."""

import weakref
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, Union

from tqdm.contrib.concurrent import thread_map

from hydroflows.workflow.method import ExpandMethod, Method

if TYPE_CHECKING:
    from hydroflows.workflow.workflow import Workflow

__all__ = ["Rule"]

FMT = ["snakemake"]


class Rule:
    """Rule class.

    A rule is the definition of a method to be run in the context of a workflow..
    The rule is responsible for detecting wildcards and expanding them based on
    the workflow wildcards.

    There is only one rule class to rule all methods, as the method is the one
    that defines the input, output and parameters of the rule.
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
        # set the method
        self.method: Method = method
        # set rule id which defaults to method name
        if rule_id is None:
            rule_id = method.name
        self.rule_id: str = str(rule_id)
        # add weak reference to workflow to avoid circular references
        self._workflow_ref = weakref.ref(workflow)

        # placeholders for wildcards detection
        self._wildcard_fields: List[str] = []
        self._wildcards: Dict[str, List] = {}

    def __repr__(self) -> str:
        """Return the representation of the rule."""
        repr_dict = {
            "id": self.rule_id,
            "method": self.method.name,
            "runs": self.n_runs,
        }
        for key, values in self.wildcards.items():
            if values:
                repr_dict[key] = values
        repr_str = ", ".join([f"{k}={v}" for k, v in repr_dict.items()])
        return f"Rule({repr_str})"

    @property
    def workflow(self) -> "Workflow":
        """Return the workflow."""
        return self._workflow_ref()

    @property
    def n_runs(self) -> int:
        """Return the number of required method runs."""
        return len(self.wildcard_product())

    @property
    def wildcards(self) -> Dict[str, List]:
        """Return the wildcards of the rule.

        Wildcards are saved for three categories, based on whether these
        "expand" (1:n), "reduce" (n:1) and "explode" (n:n) the method.
        """
        if not self._wildcards:
            self._detect_wildcards()
        return self._wildcards

    @property
    def wildcard_fields(self) -> Dict[str, List]:
        """Return the parameter fields with wildcards, per wildcard."""
        if not self._wildcard_fields:
            self._detect_wildcards()
        return self._wildcard_fields

    @property
    def _all_wildcard_fields(self) -> List[str]:
        """Return all fields with wildcards."""
        return list(set(sum(self.wildcard_fields.values(), [])))

    @property
    def _all_wildcards(self) -> List[str]:
        """Return all wildcards."""
        return list(set(sum(self.wildcards.values(), [])))

    ## SERIALIZATION METHODS

    def to_dict(self) -> Dict:
        """Return the rule as a dictionary."""
        out = {
            "method": self.method.name,
            "kwargs": self.method.kwargs_with_refs,
        }
        if self.rule_id != self.method.name:
            out["rule_id"] = self.rule_id
        return out

    ## WILDCARD METHODS

    def _detect_wildcards(self) -> None:
        """Detect wildcards based on known workflow wildcard names."""
        # add expand wildcards to workflow wildcards
        if isinstance(self.method, ExpandMethod):
            for wc, val in self.method.expand_values.items():
                self.workflow.wildcards.set(wc, val)

        # check for wildcards in input and output
        known_wildcards = self.workflow.wildcards.names
        wildcards: Dict[str, List] = {"input": [], "output": [], "params": []}
        wildcard_fields: Dict[str, List] = {}
        for sec in wildcards.keys():
            for field, value in self.method.dict[sec].items():
                if not isinstance(value, (str, Path)):
                    continue
                value = str(value)
                for wc in known_wildcards:
                    if "{" + str(wc) + "}" in value:
                        if wc not in wildcards[sec]:
                            wildcards[sec].append(wc)
                        if wc not in wildcard_fields:
                            wildcard_fields[wc] = []
                        wildcard_fields[wc].append(field)

        # organize wildcards in expand, reduce and explode
        wc_in_params = set(wildcards["input"] + wildcards["params"])
        wc_out = set(wildcards["output"])
        wildcards_dict = {
            "explode": list(wc_in_params & wc_out),
            "expand": list(wc_out - wc_in_params),
            "reduce": list(wc_in_params - wc_out),
        }

        # set the wildcard properties
        self._wildcards = wildcards_dict
        self._wildcard_fields = wildcard_fields

    def method_wildcard_instance(self, wildcards: Dict) -> Method:
        """Return a new method instance with wildcards replaced by values."""
        if not wildcards:
            return self.method

        kwargs = self.method.kwargs.copy()
        for key in kwargs:
            if key in self._all_wildcard_fields:
                if not any(isinstance(v, list) for v in wildcards.values()):
                    # explode method
                    # wildcards = {wc: v, ...}
                    kwargs[key] = str(kwargs[key]).format(**wildcards)
                else:
                    # reduce method -> turn values into lists
                    # wildcards = {wc: [v1, v2, ...], ...}
                    wc_values: List[Tuple] = list(product(*wildcards.values()))
                    kwargs[key] = [
                        str(kwargs[key]).format(**dict(zip(wildcards.keys(), wc)))
                        for wc in wc_values
                    ]
        return self.method.from_kwargs(**kwargs)

    def wildcard_product(self) -> List[Dict[str, str]]:
        """Return the values of wildcards per run."""
        # only explode if there are wildcards on the output
        wildcards = self.wildcards["explode"]
        wc_values = [self.workflow.wildcards.get(wc) for wc in wildcards]
        # drop None from list of values; this occurs when the workflow is not fully initialized yet
        wc_values = [v for v in wc_values if v is not None]
        wc_tuples: List[Tuple] = list(product(*wc_values))
        wc_product: List[Dict] = [
            dict(zip(wildcards, list(wc_val))) for wc_val in wc_tuples
        ]
        # add reduce wildcards
        for wc in self.wildcards["reduce"]:
            wc_val = self.workflow.wildcards.get(wc)
            wc_product = [{**wc_dict, wc: wc_val} for wc_dict in wc_product]

        return wc_product

    ## RUN METHODS

    def run(
        self,
        max_workers=1,
        dryrun: bool = False,
        missing_file_error: bool = False,
    ) -> None:
        """Run the rule.

        Parameters
        ----------
        max_workers : int, optional
            The maximum number of workers to use, by default 1
        dryrun : bool, optional
            Whether to run in dryrun mode, by default False
        missing_file_error : bool, optional
            Whether to raise an error if a file is missing, by default False
        """
        wildcard_product = self.wildcard_product()
        nruns = len(wildcard_product)
        if dryrun or nruns == 1 or max_workers == 1:
            for i, wildcards in enumerate(wildcard_product):
                print(f"Run {i+1}/{nruns}: {wildcards}")
                self._run_method_instance(
                    wildcards, dryrun=dryrun, missing_file_error=missing_file_error
                )
        else:
            tqdm_kwargs = {}
            if max_workers is not None:
                tqdm_kwargs.update(max_workers=max_workers)
            thread_map(self._run_method_instance, wildcard_product, **tqdm_kwargs)

    def _run_method_instance(
        self, wildcards: Dict, dryrun: bool = False, missing_file_error: bool = False
    ) -> None:
        """Run a method instance with the given kwargs."""
        m = self.method_wildcard_instance(wildcards)
        if dryrun:
            m.dryrun(missing_file_error=missing_file_error)
        else:
            m.run_with_checks()


class Rules:
    """Rules class.

    Rules are dynamically stored as attributes of the Rules class for easy access.
    The order of rules is stored in the rules attribute.
    """

    def __init__(self, rules: Optional[List[Rule]] = None) -> None:
        self.names: List[str] = []
        """Ordered list of rule IDs."""

        if rules:
            for rule in rules:
                self.set_rule(rule)

    def __repr__(self) -> str:
        """Return the representation of the rules."""
        rules_repr = "\n".join([str(self.get_rule(name)) for name in self.names])
        return f"[{rules_repr}]"

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
        if isinstance(key, int) and key < len(self.names):
            key = self.names[key]
        if key not in self.names:
            raise ValueError(f"Rule {key} not found.")
        rule: Rule = getattr(self, key)
        return rule

    def __setitem__(self, key: str, rule: Rule) -> None:
        if not isinstance(rule, Rule):
            raise ValueError("Rule should be an instance of Rule.")
        if hasattr(self, key):
            raise ValueError(f"Rule {key} already exists.")
        setattr(self, key, rule)
        self.names.append(key)

    def __iter__(self) -> Iterator[Rule]:
        return iter([self[rule_id] for rule_id in self.names])

    def __next__(self) -> Rule:
        return next(self)

    def __len__(self) -> int:
        return len(self.names)
