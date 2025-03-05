"""HydroFlows Rule class."""

import logging
import weakref
from itertools import chain, product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, Union

from tqdm.contrib.concurrent import thread_map

from hydroflows.utils.parsers import get_wildcards, has_wildcards
from hydroflows.utils.path_utils import cwd
from hydroflows.workflow.method import ExpandMethod, Method, ReduceMethod
from hydroflows.workflow.wildcards import resolve_wildcards

if TYPE_CHECKING:
    from hydroflows.workflow.workflow import Workflow

__all__ = ["Rule"]

logger = logging.getLogger(__name__)


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

        # placeholders
        self._wildcard_fields: Dict[str, List] = {}  # wildcard - fieldname dictionary
        self._wildcards: Dict[str, List] = {}  # explode, expand, reduce wildcards
        self._method_instances: List[Method] = []  # list of method instances
        # values of input, output and params fields for all method instances
        self._input: Dict[str, list[Path]] = {}
        self._output: Dict[str, list[Path]] = {}
        self._dependency: str | None = None  # rule_id of last occurring dependency
        self._loop_depth: int = 0  # loop depth of the rule

        # add expand wildcards to workflow wildcards
        if isinstance(self.method, ExpandMethod):
            for wc, val in self.method.expand_wildcards.items():
                self.workflow.wildcards.set(wc, val)

        # detect and validate wildcards
        self._detect_wildcards()
        self._validate_wildcards()
        self._create_references_for_method_inputs()
        self._add_method_params_to_config()
        self._set_method_instances()
        self._set_input_output()
        self._detect_dependency()

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
        return len(self._method_instances)

    @property
    def wildcards(self) -> Dict[str, List]:
        """Return the wildcards of the rule per wildcard type.

        Wildcards are saved for three types, based on whether these
        "expand" (1:n), "reduce" (n:1) and "explode" (n:n) the method.
        """
        return self._wildcards

    @property
    def wildcard_fields(self) -> Dict[str, List]:
        """Return a wildcard - fieldname dictionary.

        Per wildcard it contains all input, output and params field names which have the wildcard.
        """
        return self._wildcard_fields

    @property
    def method_instances(self) -> List[Method]:
        """Return a list of all method instances."""
        return self._method_instances

    @property
    def input(self) -> Dict[str, list[Path]]:
        """Return the input paths of the rule per field."""
        return self._input

    @property
    def output(self) -> Dict[str, list[Path]]:
        """Return the output paths of the rule per field."""
        return self._output

    @property
    def dependency(self) -> str | None:
        """Return the rule_id of the last occurring dependency."""
        return self._dependency

    @property
    def _all_wildcard_fields(self) -> List[str]:
        """Return all input, output, and params fields with wildcards."""
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
                    logger.warning(f"Wildcard {wc} not found in workflow wildcards.")

        # organize wildcards in expand, reduce and explode
        wc_in = set(wildcards["input"] + wildcards["params"])
        wc_out = set(wildcards["output"])
        wildcards_dict = {
            "explode": list(wc_in & wc_out),
            "expand": list(wc_out - wc_in),
            "reduce": list(wc_in - wc_out),
        }

        # set the wildcard properties
        self._wildcards = wildcards_dict
        self._wildcard_fields = wildcard_fields
        self._loop_depth = len(self.wildcards["explode"])

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

    def _create_method_instance(self, wildcards: Dict[str, str | list[str]]) -> Method:
        """Return a new method instance with wildcards replaced by values.

        Parameters
        ----------
        wildcards : Dict[str, str | list[str]]
            The wildcards to replace in the method instance.
            For explode wildcards, the value should be a single string.
            For reduce wildcards, the value should be a list of strings.
            Expand wildcards are only on the output and are set in the method.
        """
        # explode kwargs should always be a single value;
        for wc in self.wildcards["explode"]:
            if not isinstance(wildcards[wc], str):
                raise ValueError({f"Explode wildcard '{wc}' should be a string."})
        # reduce should be lists;
        for wc in self.wildcards["reduce"]:
            if not isinstance(wildcards[wc], list):
                raise ValueError(f"Reduce wildcard '{wc}' should be a list.")
        # expand wildcards should not be in instance wildcards -> only inputs
        for wc in self.wildcards["expand"]:
            if wc in wildcards:
                raise ValueError(f"Expand wildcard '{wc}' should not be in wildcards.")

        # get kwargs from method
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
                kwargs[key] = [
                    resolve_wildcards(kwargs[key], d) for d in wildcards_reduce
                ]
            elif key in self._all_wildcard_fields:
                # explode method
                # wildcards = {wc: v, ...}
                kwargs[key] = resolve_wildcards(kwargs[key], wildcards)
        method = self.method.from_kwargs(**kwargs)
        return method

    @property
    def _wildcard_product(self) -> List[Dict[str, str]]:
        """Return the values of wildcards per method instance."""
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
        """Create references for method inputs based on output paths of previous rules."""
        output_path_refs = self.workflow._output_path_refs
        # unpack existing config
        conf_keys = self.workflow.config.keys
        conf_values = self.workflow.config.values
        # Check on duplicate output values
        for key, value in self.method.output:
            if not isinstance(value, Path):
                continue
            value = value.as_posix()
            if value in output_path_refs:
                duplicate_field = output_path_refs[value].replace("$rules.", "")
                raise ValueError(
                    "All output file paths must be unique. "
                    f"{self.rule_id}.output.{key} ({value}) is already an output of {duplicate_field}"
                )
        for key, value in self.method.input:
            # Skip if key is already present in input refs
            if key in self.method.input._refs or value is None:
                continue
            if isinstance(value, Path):
                value = value.as_posix()
            if value in list(output_path_refs.keys()):
                self.method.input._refs.update({key: output_path_refs[value]})
            # Check if value already exists in conf and update ref if so
            elif value in conf_values:
                conf_key = conf_keys[conf_values.index(value)]
                self.method.input._refs.update({key: "$config." + conf_key})
            else:
                config_key = f"{self.rule_id}_{key}"
                logger.debug("Adding %s to config", config_key)
                # Add input to config
                self.workflow.config = self.workflow.config.model_copy(
                    update={config_key: value}
                )
                # Replace method input with reference to config
                config_ref = "$config." + config_key
                self.method.input._refs.update({key: config_ref})

    def _add_method_params_to_config(self) -> None:
        """Add method parameters to the config and update the method params refs."""
        # unpack existing config
        conf_keys = self.workflow.config.keys
        conf_values = self.workflow.config.values
        for p in self.method.params:
            key, value = p
            # Check if key can be found in method Params class
            if key in self.method.params.model_fields:
                default_value = self.method.params.model_fields.get(key).default
            else:
                default_value = None

            # Skip if key is already a ref
            if key in self.method.params._refs:
                continue
            # Skip if param value has wildcard
            elif has_wildcards(value):
                continue
            # Check if value already exists in conf and update ref if so
            elif value in conf_values:
                conf_key = conf_keys[conf_values.index(value)]
                self.method.params._refs.update({key: "$config." + conf_key})

            elif value != default_value:
                config_key = f"{self.rule_id}_{key}"
                self.workflow.config = self.workflow.config.model_copy(
                    update={config_key: value}
                )
                config_ref = "$config." + config_key
                logging.debug("Adding %s to config", config_key)
                self.method.params._refs.update({key: config_ref})

    def _set_method_instances(self):
        """Set a list with all instances of the method based on the wildcards."""
        self._method_instances = []
        for wildcard_dict in self._wildcard_product:
            method = self._create_method_instance(wildcard_dict)
            self._method_instances.append(method)

    def _set_input_output(self):
        """Set the input and output paths dicts of the rule."""
        parameters = {"input": {}, "output": {}}
        for method in self._method_instances:
            for name in parameters:
                if name == "output" and isinstance(method, ExpandMethod):
                    obj = method.output_expanded.items()
                else:
                    obj = getattr(method, name)
                for key, value in obj:
                    if key not in parameters[name]:
                        parameters[name][key] = []
                    if not isinstance(value, list):
                        value = [value]
                    if not isinstance(value[0], Path):
                        continue
                    # Removes duplicates
                    # Using set() does not preserve insertion order, this does and also filters uniques
                    for val in value:
                        if val not in parameters[name][key]:
                            parameters[name][key].append(val)

        # set input and output parameters
        self._input = parameters["input"]
        self._output = parameters["output"]

    def _detect_dependency(self):
        """Find last occuring dependency of self by matching input values to output values of prev rules."""
        # Make list of inputs, convert to set of strings for quick matching
        inputs = self._input
        inputs = list(chain(*inputs.values()))
        # order of inputs doesn't matter here so set() is fine
        inputs = set([str(item) for item in inputs])

        # Init dependency as None
        for rule in reversed(self.workflow.rules):
            # Make list of outputs as strings, outputs always paths anyways
            outputs = rule._output
            outputs = list(chain(*outputs.values()))
            outputs = [str(item) for item in outputs]

            # Find if inputs, outputs share any element
            if not inputs.isdisjoint(outputs):
                self._dependency = rule.rule_id
                break

    ## RUN METHODS
    def run(self, max_workers=1) -> None:
        """Run the rule.

        Parameters
        ----------
        max_workers : int, optional
            The maximum number of workers to use, by default 1
        """
        nruns = self.n_runs
        # set working directory to workflow root
        with cwd(self.workflow.root):
            if nruns == 1 or max_workers == 1:
                for i, method in enumerate(self._method_instances):
                    msg = f"Running {self.rule_id} {i + 1}/{nruns}"
                    logger.info(msg)
                    method.run_with_checks()
            else:
                tqdm_kwargs = {}
                if max_workers is not None:
                    tqdm_kwargs.update(max_workers=max_workers)
                thread_map(
                    lambda method: method.run_with_checks(),
                    self._method_instances,
                    **tqdm_kwargs,
                )

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
        nruns = self.n_runs
        input_files = input_files or []
        output_files = []
        # set working directory to workflow root
        with cwd(self.workflow.root):
            for i, method in enumerate(self._method_instances):
                msg = f"Running {self.rule_id} {i + 1}/{nruns}"
                logger.info(msg)
                output_files_i = method.dryrun(
                    missing_file_error=missing_file_error, input_files=input_files
                )
                output_files.extend(output_files_i)
        return output_files


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

    @property
    def ordered_rules(self) -> List[Rule]:
        """Return a list of all rules."""
        return [self[rule_id] for rule_id in self.names]

    def _get_new_rule_index(self, rule: Rule) -> int:
        """Determine where the rule should be added in the list."""
        if rule.dependency is not None:
            ind = self.names.index(rule.dependency) + 1
            # If there is already a rule in that position, break tie based on loop_depth with highest loop depth last
            if ind != len(self.names) and rule._loop_depth > self[ind]._loop_depth:
                ind += 1
        # If rule input does not depend on others, put at beginning after other rules with no input dependencies.
        else:
            ind = len([rule for rule in self.ordered_rules if rule.dependency is None])
        return ind

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
        ind = self._get_new_rule_index(rule)
        self.names.insert(ind, key)

    def __iter__(self) -> Iterator[Rule]:
        return iter([self[rule_id] for rule_id in self.names])

    def __next__(self) -> Rule:
        return next(self)

    def __len__(self) -> int:
        return len(self.names)
