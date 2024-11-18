"""HydroFlows Rule class."""

import warnings
import weakref
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, Union

from tqdm.contrib.concurrent import thread_map

from hydroflows.utils.parsers import get_wildcards
from hydroflows.workflow.method import ExpandMethod, Method, ReduceMethod

if TYPE_CHECKING:
    from hydroflows.workflow.method_parameters import Parameters
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

        # add expand wildcards to workflow wildcards
        if isinstance(self.method, ExpandMethod):
            for wc, val in self.method.expand_wildcards.items():
                self.workflow.wildcards.set(wc, val)

        # detect and validate wildcards
        self._detect_wildcards()
        self._validate_wildcards()

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

    @property
    def input(self) -> "Parameters":
        """Return the input parameters of the method."""
        return self.method.input

    @property
    def output(self) -> "Parameters":
        """Return the output parameters of the method."""
        return self.method.output

    @property
    def params(self) -> "Parameters":
        """Return the parameters of the method."""
        return self.method.params

    ## SERIALIZATION METHODS

    def to_dict(self) -> Dict:
        """Return the rule as a dictionary."""
        out = {
            "method": self.method.name,
            "kwargs": self.method.to_kwargs(return_refs=True, posix_path=True),
        }
        if self.rule_id != self.method.name:
            out["rule_id"] = self.rule_id
        return out

    ## WILDCARD METHODS

    def _detect_wildcards(self) -> None:
        """Detect wildcards based on known workflow wildcard names."""
        # check for wildcards in input and output
        known_wildcards = self.workflow.wildcards.names
        wildcards: Dict[str, List] = {"input": [], "output": [], "params": []}
        wildcard_fields: Dict[str, List] = {}
        for sec in wildcards.keys():
            for field, value in self.method.dict[sec].items():
                if not isinstance(value, (str, Path)):
                    continue
                val_wildcards = get_wildcards(value)
                # loop over wildcards that are known and in the value
                for wc in set(val_wildcards) & set(known_wildcards):
                    if wc not in wildcards[sec]:
                        wildcards[sec].append(wc)
                    if wc not in wildcard_fields:
                        wildcard_fields[wc] = []
                    wildcard_fields[wc].append(field)
                # loop over wildcards that are not known
                for wc in set(val_wildcards) - set(known_wildcards):
                    # raise warning if wildcard is not known
                    warnings.warn(
                        f"Wildcard {wc} not found in workflow wildcards.", stacklevel=2
                    )

        # organize wildcards in expand, reduce and explode
        wc_in = set(wildcards["input"])
        wc_out = set(wildcards["output"])
        wildcards_dict = {
            "explode": list(wc_in & wc_out),
            "expand": list(wc_out - wc_in),
            "reduce": list(wc_in - wc_out),
        }

        # set the wildcard properties
        self._wildcards = wildcards_dict
        self._wildcard_fields = wildcard_fields

    def _validate_wildcards(self) -> None:
        """Validate wildcards based on method type."""
        msg = ""
        if isinstance(self.method, ExpandMethod) and not self.wildcards["expand"]:
            msg = f"ExpandMethod {self.method.name} requires a new expand wildcard on output (Rule {self.rule_id})."
        elif isinstance(self.method, ReduceMethod) and not self.wildcards["reduce"]:
            msg = f"ReduceMethod {self.method.name} requires a reduce wildcard on input only (Rule {self.rule_id})."
        elif self.wildcards["expand"] and not isinstance(self.method, ExpandMethod):
            wcs = self.wildcards["expand"]
            msg = f"Wildcard(s) {wcs} missing on input or method {self.method.name} should be an ExpandMethod (Rule {self.rule_id})."
        elif self.wildcards["reduce"] and not isinstance(self.method, ReduceMethod):
            wcs = self.wildcards["reduce"]
            msg = f"Wildcard(s) {wcs} missing on output or method {self.method.name} should be a ReduceMethod (Rule {self.rule_id})."
        if msg:
            raise ValueError(msg)

    def _method_wildcard_instance(self, wildcards: Dict) -> Method:
        """Return a new method instance with wildcards replaced by values.

        Parameters
        ----------
        wildcards : Dict
            The reduce and explode wildcards to replace in the method.
            Expand wildcards are only on the output and are set in the method.
        """
        if not wildcards:
            return self.method
        # explode kwargs should always be a single value;
        for wc in self.wildcards["explode"]:
            assert not isinstance(
                wildcards[wc], list
            ), f"Explode wildcard '{wc}' should be a single value."
        # reduce should be lists;
        for wc in self.wildcards["reduce"]:
            assert isinstance(
                wildcards[wc], list
            ), f"Reduce wildcard '{wc}' should be a list."
        # expand wildcards should not be in instance wildcards -> only inputs
        for wc in self.wildcards["expand"]:
            assert (
                wc not in wildcards
            ), f"Expand wildcard '{wc}' should not be in wildcards."

        kwargs = self.method.to_kwargs()
        # get input fields over which the method should reduce
        reduce_fields = []
        for wc in self.wildcards["reduce"]:
            reduce_fields.extend(self.wildcard_fields[wc])
        reduce_fields = list(set(reduce_fields))  # keep unique values
        if reduce_fields:
            # make sure all values are a list
            # then take the product of the lists
            wc_list = [
                val if isinstance(val, list) else [val] for val in wildcards.values()
            ]
            wildcards_reduce: List[Dict] = [
                dict(zip(wildcards.keys(), wc)) for wc in list(product(*wc_list))
            ]
        for key in kwargs:
            if key in reduce_fields:
                # reduce method -> turn values into lists
                # wildcards = {wc: [v1, v2, ...], ...}
                kwargs[key] = [str(kwargs[key]).format(**d) for d in wildcards_reduce]
            elif key in self._all_wildcard_fields:
                # explode method
                # wildcards = {wc: v, ...}
                kwargs[key] = str(kwargs[key]).format(**wildcards)
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

    def run(self, max_workers=1) -> None:
        """Run the rule.

        Parameters
        ----------
        max_workers : int, optional
            The maximum number of workers to use, by default 1
        """
        wildcard_product = self.wildcard_product()
        nruns = len(wildcard_product)
        if nruns == 1 or max_workers == 1:
            for i, wildcards in enumerate(wildcard_product):
                print(f"Run {i+1}/{nruns}: wildcard values = {wildcards}")
                self._run_method_instance(wildcards)
        else:
            tqdm_kwargs = {}
            if max_workers is not None:
                tqdm_kwargs.update(max_workers=max_workers)
            thread_map(self._run_method_instance, wildcard_product, **tqdm_kwargs)

    def dryrun(
        self,
        input_files: Optional[List[Path]] = None,
        missing_file_error: bool = False,
    ) -> List[Path]:
        """Dryrun the rule.

        Parameters
        ----------
        input_files : List[Path], optional
            The input files to use for the dryrun, by default None
        missing_file_error : bool, optional
            Whether to raise an error if a file is missing, by default False

        Returns
        -------
        List[Path]
            The output files of the dryrun.
        """
        input_files = input_files or []
        wildcard_product = self.wildcard_product()
        nruns = len(wildcard_product)
        output_files = []
        for i, wildcards in enumerate(wildcard_product):
            print(f"Run {i+1}/{nruns}: wildcard values = {wildcards}")
            output_files_i = self._dryrun_method_instance(
                wildcards,
                missing_file_error=missing_file_error,
                input_files=input_files,
            )
            output_files.extend(output_files_i)
        return output_files

    def _run_method_instance(self, wildcards: Dict) -> None:
        """Run a method instance with the given kwargs."""
        m = self._method_wildcard_instance(wildcards)
        return m.run_with_checks()

    def _dryrun_method_instance(
        self,
        wildcards: Dict,
        input_files: List[Path],
        missing_file_error: bool = False,
    ) -> List[Path]:
        """Dryrun a method instance with the given kwargs."""
        m = self._method_wildcard_instance(wildcards)
        return m.dryrun(missing_file_error=missing_file_error, input_files=input_files)


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
