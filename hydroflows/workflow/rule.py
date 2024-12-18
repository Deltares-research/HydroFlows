"""HydroFlows Rule class."""

import logging
import warnings
import weakref
from copy import deepcopy
from itertools import chain, product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, Union

from tqdm.contrib.concurrent import thread_map

from hydroflows.utils.parsers import get_wildcards
from hydroflows.workflow.method import ExpandMethod, Method, ReduceMethod

if TYPE_CHECKING:
    from hydroflows.workflow.method_parameters import Parameters
    from hydroflows.workflow.workflow import Workflow

__all__ = ["Rule"]

logger = logging.getLogger(__name__)

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
        self._parameter_list: Dict[
            str, Dict
        ] = {}  # lists with all inputs and outputs for method instances
        self.dependency: str | None = None  # rule id of last occuring dependency
        self._method_list: List[Method] = []  # List of method instances

        # add expand wildcards to workflow wildcards
        if isinstance(self.method, ExpandMethod):
            for wc, val in self.method.expand_wildcards.items():
                self.workflow.wildcards.set(wc, val)

        # detect and validate wildcards
        self._detect_wildcards()
        self._validate_wildcards()
        self._create_references_for_method_inputs()
        self._add_method_params_to_config()
        self._set_method_list()
        self._set_parameter_lists()
        self._detect_dependency()

        self.loop_depth = len(self.wildcards["explode"])

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
        return len(self._method_list)

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
        # TODO: Deal with expand wildcards more cleanly (after Method,Rule refactor)
        if not wildcards:
            method = deepcopy(self.method)
            if isinstance(method, ExpandMethod):
                method.expand_output_paths()
            return method
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
        method = self.method.from_kwargs(**kwargs)
        if isinstance(method, ExpandMethod):
            method.expand_output_paths()
        return method

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

    def _create_references_for_method_inputs(self):
        output_path_refs = self.workflow._output_path_refs
        # Check on duplicate output values
        for key, value in self.method.output:
            if not isinstance(value, Path):
                continue
            value = value.as_posix()
            if value in output_path_refs:
                duplicate_field = output_path_refs[value].replace("$rules.", "")
                raise ValueError(
                    f"All output file paths must be unique, {self.rule_id}.output.{key} ({value}) is already an output of {duplicate_field}"
                )
        for key, value in self.method.input:
            # Skip if key is already present in input refs
            if key in self.method.input._refs or value is None:
                continue
            if isinstance(value, Path):
                value = value.as_posix()
            if value in output_path_refs.keys():
                self.method.input._refs.update({key: output_path_refs[value]})
            else:
                config_key = f"{self.rule_id}_{key}"
                logger.debug("Adding %s to config", config_key)
                # Add input to config
                self.workflow.config = self.workflow.config.model_copy(
                    update={config_key: value}
                )
                # Replace methond input with reference to config
                config_ref = "$config." + config_key
                self.method.input._refs.update({key: config_ref})

    def _add_method_params_to_config(self) -> None:
        for p in self.method.params:
            key, value = p
            # Check if key can be found in method Params class
            if key in self.method.params.model_fields:
                default_value = self.method.params.model_fields.get(key).default
            else:
                default_value = None

            if value != default_value:
                config_key = f"{self.rule_id}_{key}"
                self.workflow.config = self.workflow.config.model_copy(
                    update={config_key: value}
                )
                config_ref = "$config." + config_key
                logging.debug("Adding %s to config", config_key)
                self.method.params._refs.update({key: config_ref})

    def _set_method_list(self):
        self._method_list = []
        for wildcard in self.wildcard_product():
            method = self._method_wildcard_instance(wildcard)
            self._method_list.append(method)

    def _set_parameter_lists(self):
        parameters = {
            "input": {},
            "output": {},
            "params": {},
        }
        for method in self._method_list:
            for name in parameters:
                for key, value in getattr(method, name):
                    if key not in parameters[name]:
                        parameters[name][key] = []
                    if name in ["input", "output"]:
                        if not isinstance(value, list):
                            value = [value]
                        if not isinstance(value[0], Path):
                            continue
                        # Removes duplicates
                        parameters[name][key] = list(set(parameters[name][key] + value))
                    else:
                        parameters[name][key].append(value)

        self._parameter_list = parameters

    def _detect_dependency(self):
        """Find last occuring dependency of self by matching input values to output values of prev rules."""
        # Make list of inputs, convert to set of strings for quick matching
        inputs = self._parameter_list["input"]
        inputs = list(chain(*inputs.values()))
        inputs = set([str(item) for item in inputs])

        # Init dependency as None
        self.dependency = None
        for rule in reversed(self.workflow.rules):
            # Make list of outputs as strings, outputs always paths anyways
            outputs = rule._parameter_list["output"]
            outputs = list(chain(*outputs.values()))
            outputs = [str(item) for item in outputs]

            # Find if inputs, outputs share any element
            if not inputs.isdisjoint(outputs):
                self.dependency = rule.rule_id
                break

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
        nruns = self.n_runs
        if dryrun or nruns == 1 or max_workers == 1:
            for i, method in enumerate(self._method_list):
                msg = f"Running {self.rule_id} {i+1}/{nruns}"
                logger.info(msg)
                self._run_method_instance(
                    method=method, dryrun=dryrun, missing_file_error=missing_file_error
                )
        else:
            tqdm_kwargs = {}
            if max_workers is not None:
                tqdm_kwargs.update(max_workers=max_workers)
            thread_map(self._run_method_instance, self._method_list, **tqdm_kwargs)

    def _run_method_instance(
        self, method: Method, dryrun: bool = False, missing_file_error: bool = False
    ) -> None:
        """Run a method instance with the given kwargs."""
        if dryrun:
            method.dryrun(missing_file_error=missing_file_error)
        else:
            method.run_with_checks()


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
        # Determine where the rule should be added in the list
        if rule.dependency is not None:
            ind = self.names.index(rule.dependency) + 1
            # If there is already a rule in that position, break tie based on loop_depth with highest loop depth last
            if ind != len(self.names) and rule.loop_depth > self[ind].loop_depth:
                ind += 1
        # If rule input does not depend on others, put at beginning after other rules with no input dependencies.
        else:
            ind = len([rule for rule in self if rule.dependency is None])
        self.names.insert(ind, key)

    def __iter__(self) -> Iterator[Rule]:
        return iter([self[rule_id] for rule_id in self.names])

    def __next__(self) -> Rule:
        return next(self)

    def __len__(self) -> int:
        return len(self.names)
