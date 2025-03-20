"""HydroFlows Rule class.

This class is responsible for:
- detecting and validating wildcards in the method.
- creating method instances based on the wildcards.
- parsing input, and output paths of the rule (i.e. for all method instances).
- running the rule (i.e. running all method instances).
"""

import logging
import weakref
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from tqdm.contrib.concurrent import thread_map

from hydroflows.utils.parsers import get_wildcards
from hydroflows.utils.path_utils import cwd
from hydroflows.workflow.method import ExpandMethod, Method, ReduceMethod
from hydroflows.workflow.method_parameters import Parameters
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

    There is one common rule class to rule all methods.
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
        self._wildcards: Dict[str, List] = {}  # repeat, expand, reduce wildcards
        self._loop_depth: int = 0  # loop depth of the rule (based on repeat wildcards)
        self._method_instances: List[Method] = []  # list of method instances
        self._input: Dict[str, list[Path]] = {}  # input paths for all method instances
        self._output: Dict[
            str, list[Path]
        ] = {}  # output paths for all method instances
        self._output_refs: Dict[str, str] = {}  # output path references

        # add expand wildcards to workflow wildcards
        if isinstance(self.method, ExpandMethod):
            for wc, val in self.method.expand_wildcards.items():
                self.workflow.wildcards.set(wc, val)

        # detect and validate wildcards
        self._detect_wildcards()
        self._validate_wildcards()
        # get method instances and in- and output paths
        self._set_method_instances()
        self._set_input_output()
        # add references to other rule outputs and config
        self._create_references_for_method_inputs()

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
        "expand" (1:n), "reduce" (n:1) and "repeat" (n:n) the method.
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
            for field, value in getattr(self.method, sec):
                # skip if value is not a string or path
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

        # organize wildcards in expand, reduce and repeat
        wc_in = set(wildcards["input"] + wildcards["params"])
        wc_out = set(wildcards["output"])
        wildcards_dict = {
            "repeat": list(wc_in & wc_out),
            "expand": list(wc_out - wc_in),
            "reduce": list(wc_in - wc_out),
        }

        # set the wildcard properties
        self._wildcards = wildcards_dict
        self._wildcard_fields = wildcard_fields
        self._loop_depth = len(self.wildcards["repeat"])

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
            For repeat wildcards, the value should be a single string.
            For reduce wildcards, the value should be a list of strings.
            Expand wildcards are only on the output and are set in the method.
        """
        # repeat kwargs should always be a single value;
        for wc in self.wildcards["repeat"]:
            if not isinstance(wildcards[wc], str):
                raise ValueError({f"Repeat wildcard '{wc}' should be a string."})
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
                # repeat method
                # wildcards = {wc: v, ...}
                kwargs[key] = resolve_wildcards(kwargs[key], wildcards)
        method = self.method.from_kwargs(**kwargs)
        return method

    @property
    def _wildcard_product(self) -> List[Dict[str, str]]:
        """Return the values of wildcards per method instance."""
        # only repeat if there are wildcards on the output
        wildcards = self.wildcards["repeat"]
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

    @property
    def _output_path_refs(self) -> Dict[str, str]:
        """Retrieve output path references of rule method.

        Returns
        -------
        Dict[str, str]
            Dictionary containing the output path as the key and the reference as the value
        """
        if not self._output_refs:
            for key, value in self.method.output:
                if isinstance(value, Path):
                    value = value.as_posix()
                    self._output_refs[value] = f"$rules.{self.rule_id}.output.{key}"
        return self._output_refs

    def _create_references_for_method_inputs(self):
        """Create references for method inputs based on output paths of previous rules."""
        # chain all output_path_refs of previous rules together
        output_path_refs = {}
        for rule in self.workflow.rules:
            output_path_refs.update(rule._output_path_refs)
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
                    inout_dict = method.output_expanded
                else:
                    obj: Parameters = getattr(method, name)
                    inout_dict = {key: getattr(obj, key) for key in obj.all_fields}
                for key, value in inout_dict.items():
                    if key not in parameters[name]:
                        parameters[name][key] = []
                    if name in ["input", "output"]:
                        if not isinstance(value, list):
                            value = [value]
                        if not isinstance(value[0], Path):
                            continue
                        # Removes duplicates
                        # Using set() does not preserve insertion order, this does and also filters uniques
                        for val in value:
                            if val not in parameters[name][key]:
                                parameters[name][key].append(val)
                    elif value not in parameters[name][key]:
                        parameters[name][key].append(value)

        self._input = parameters["input"]
        self._output = parameters["output"]

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
                    method.run()
            else:
                tqdm_kwargs = {}
                if max_workers is not None:
                    tqdm_kwargs.update(max_workers=max_workers)
                thread_map(
                    lambda method: method.run(),
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
