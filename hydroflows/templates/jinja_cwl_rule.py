from copy import deepcopy
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Union

from hydroflows._typing import folderpath
from hydroflows.utils.cwl_utils import map_cwl_types
from hydroflows.utils.parsers import get_wildcards

if TYPE_CHECKING:
    from hydroflows.workflow.rule import Rule


class JinjaCWLRule:
    """Class for exporting to CWL"""

    def __init__(self, rule: "Rule"):
        self.rule = rule
        self.id = rule.rule_id
        self.method_name = rule.method.name
        self.loop_depth = rule._loop_depth

        self._input: Dict[str, Dict] = {}
        self._input_wildcards: list[str] = []
        self._output: Dict[str, Dict] = {}

        self._set_input()
        self._set_input_wildcards()
        self._set_output()

    @property
    def input(self) -> Dict[str, Dict]:
        """Return nested dict of input keys and CWL info."""
        return self._input

    @property
    def output(self) -> Dict[str, Dict]:
        """Return nested dict of output keys and CWL info."""
        return self._output

    @property
    def input_wildcards(self) -> List[str]:
        """Return list of explode wildcards occuring in inputs."""
        return self._input_wildcards

    def _set_input(self) -> Dict[str, str]:
        """Get input dict for CWL step."""
        refs = self.rule.method.input.to_dict(filter_types=Path, return_refs=True)
        inputs = {}
        # Reduce wildcards determines type File[] vs type File
        reduce_wc = None
        if self.rule.wildcards["reduce"]:
            (reduce_wc,) = self.rule.wildcards["reduce"]

        for key, val in refs.items():
            ref = self.rule.workflow.get_ref(val)
            inputs[key] = map_cwl_types(ref.value)
            # Set the source of the input (from prev rule, config)
            if "$config" in ref.ref:
                inputs[key]["source"] = val.split(".")[-1]
            if "$rules" in ref.ref:
                tmp = val.split(".")
                inputs[key]["source"] = f"{tmp[-3]}/{tmp[-1]}"
            # Set input type
            if reduce_wc and key in self.rule.wildcard_fields[reduce_wc]:
                inputs[key]["type"] += "[]"
        # Add params to inputs
        params = self.rule.method.params.to_dict(return_refs=True)
        for key, val in params.items():
            default_value = self.rule.method.params.model_fields.get(key).default
            if val == default_value:
                continue
            # Set source for input to correct reference
            if isinstance(val, str) and "$" in val:
                inputs[key] = map_cwl_types(self.rule.method.params.to_dict()[key])
                inputs[key]["source"] = val.split(".")[-1]
                # wildcards have _wc added when turned into workflow inputs
                if "wildcards" in val:
                    inputs[key]["source"] += "_wc"
            else:
                inputs[key] = map_cwl_types(val)
            inputs[key]["type"] += "?"

        self._input = inputs

    def _set_input_wildcards(self) -> str:
        """Get wildcards that need to be included in CWL step input."""
        if self.rule.wildcards["explode"]:
            wc = self.rule.wildcards["explode"]
            wc = [item + "_wc" for item in wc]
            self._input_wildcards = wc

    def _set_output(self) -> Dict[str, str]:
        """Get outputs of CWL step."""
        results = self.rule.method.output.to_dict(mode="python", filter_types=Path)
        outputs = {}
        wc_expand = self.rule.wildcards["expand"]
        for key, val in results.items():
            outputs[key] = {"value": [val.as_posix()]}
            if isinstance(val, folderpath):
                outputs[key]["type"] = "Directory"
                outputs[key]["value"] = [val.parent.as_posix()]
            else:
                outputs[key]["type"] = "File"
            if self.input_wildcards:
                # This is for explode (n-to-n) methods.
                # We dont want every possible output value here
                # only replace {wildcard} by CWL-style $(input.wildcard)
                for wc in self.input_wildcards:
                    wc = wc.split("_")[0]
                    outputs[key]["value"] = [
                        item.replace(("{" + f"{wc}" + "}"), f"$(inputs.{wc}_wc)")
                        for item in outputs[key]["value"]
                    ]
            if wc_expand and any(get_wildcards(val, wc_expand)):
                # This is for expand (1-to-n) methods
                # Here we want every possible value for the expand wildcards
                wc_dict = self.rule.method.expand_wildcards
                wc_values = list(product(*wc_dict.values()))
                # output[key]["value"] is a singleton list before filling in wildcard values
                outputs[key]["value"] = [
                    outputs[key]["value"][0].format(**dict(zip(wc_expand, wc)))
                    for wc in wc_values
                ]
                outputs[key]["type"] += "[]"

        self._output = outputs


class JinjaCWLWorkflow:
    """Class for exporting workflow to CWL."""

    def __init__(self, rules: List[JinjaCWLRule], start_loop_depth: int = 0):
        self.rules = rules
        self.workflow = rules[0].rule.workflow
        self.start_loop = start_loop_depth
        self.id = f"subworkflow_{rules[0].id}"

        self._steps: List[Union[JinjaCWLRule, "JinjaCWLWorkflow"]] = []
        self._input: Dict[str, Dict] = {}
        self._output: Dict[str, Dict] = {}
        self._input_scatter: List[str] = []

        self._set_steps()
        self._set_output()
        self._set_input()
        # input scatter only needed for subworkflows
        if self.start_loop > 0:
            self._set_input_scatter()

    @property
    def steps(self) -> List[Union[JinjaCWLRule, "JinjaCWLWorkflow"]]:
        """Return list of steps and subworkflows."""
        return self._steps

    @property
    def input(self) -> Dict[str, Dict]:
        """Return nested dict of input keys and info."""
        return self._input

    @property
    def output(self) -> Dict[str, Dict]:
        """Return nest dict of output keys and info."""
        return self._output

    @property
    def input_scatter(self) -> List[str]:
        """Return list of inputs that are scattered over in CWL workflow."""
        return self._input_scatter

    def _set_steps(self):
        """Set list of steps and subworkflows."""
        step_list = deepcopy(self.rules)

        sub_wf = [rule for rule in step_list if rule.loop_depth > self.start_loop]
        indices = [i for i, x in enumerate(step_list) if x in sub_wf]

        if sub_wf:
            step_list[indices[0] : indices[-1] + 1] = [
                JinjaCWLWorkflow(rules=sub_wf, start_loop_depth=self.start_loop + 1)
            ]

        self._steps = step_list

    def _set_input(self):
        """Set CWL workflow inputs to be workflog.config + wildcards."""
        input_dict = {}
        conf_keys = self.workflow.config.keys
        conf_values = self.workflow.config.values
        ids = [rule.id for rule in self.rules]
        step_ids = [step.id for step in self.steps]

        # copy inputs from steps
        for step in self.steps:
            if isinstance(step, JinjaCWLRule):
                ins = deepcopy(step.input)
                for key, info in ins.items():
                    # Set correct format for input source
                    if "source" in info and "/" not in info["source"]:
                        if info["source"] in conf_keys:
                            in_val = conf_values[conf_keys.index(info["source"])]
                        elif info["source"] in self.workflow.wildcards.names:
                            in_val = self.workflow.wildcards.get(info["source"])
                        else:
                            in_val = info["value"]
                        input_dict[info["source"]] = map_cwl_types(in_val)
                    elif "source" in info:
                        if key in input_dict:
                            input_dict[key + f"_{step.id}"] = info
                        else:
                            input_dict[key] = info
                        if not any([id in info["source"] for id in step_ids]):
                            step._input[key]["source"] = key
            # Copy inputs from subworkflow
            elif isinstance(step, JinjaCWLWorkflow):
                ins = deepcopy(step.input)
                for key in ins:
                    if key in list(self.output.keys()):
                        ins[key]["source"] = self.output[key]["outputSource"]
                input_dict.update(ins)

        # Delete any inputs with sources to other steps
        tmp = deepcopy(input_dict)
        for key, info in tmp.items():
            if "source" in info:
                if any([id in info["source"] for id in ids]):
                    input_dict.pop(key)

        # Add wildcards to input
        for wc in self.rules[0].input_wildcards:
            input_dict.update({wc: {"type": "string[]", "source": wc}})

        self._input = input_dict

    def _set_output(self):
        """Set CWL workflow outputs to be outputs of all rules."""
        output_dict = {}

        # copy outputs from cwl rule
        for step in self.steps:
            for id, info in step.output.items():
                output_dict[id] = {
                    "type": info["type"],
                    "outputSource": f"{step.id}/{id}",
                    "value": info["value"],
                }
                # Make sure outputs produced by subworkflows are labeled as array outputs
                # This can give output types with [][], corrected for in jinja template
                if "subworkflow" in output_dict[id]["outputSource"]:
                    output_dict[id]["type"] += "[]"
        self._output = output_dict

    def _set_input_scatter(self) -> List[str]:
        """Set inputs which need to be scattered over."""
        wc = self.rules[0].rule.wildcards["explode"]
        ins = self.input
        scatters = []

        # Fetch all inputs with relevant wildcard
        for key, info in ins.items():
            if info["type"] == "File":
                val = info["value"]["path"]
            elif "value" in info:
                val = info["value"]
            else:
                continue
            if get_wildcards(val, wc):
                scatters.append(key)
                if "[]" in info["type"]:
                    self._input[key]["type"] = info["type"].replace("[]", "")

        for item in wc:
            scatters.append(item + "_wc")

        # Make sure the correct wildcards are treated as single input vs array input
        for key, info in ins.items():
            if "_wc" in key:
                # wildcards that are scattered over should be single input
                if key in scatters and "[]" in info["type"]:
                    self._input[key]["type"] = self._input[key]["type"].replace(
                        "[]", ""
                    )
                # Wildcards that are only scattered over in a subworkflow should be array inputs
                if key not in scatters and "[]" not in info["type"]:
                    self._input[key]["type"] += "[]"

        # Correct input_scatter of subworkflow
        for step in self.steps:
            if isinstance(step, JinjaCWLWorkflow):
                scatter_keys = [key for key in step.input_scatter if "_wc" not in key]
                scatter_vals = [step.input[key]["value"] for key in scatter_keys]
                scatter_vals = [
                    val["path"] if isinstance(val, Dict) else val
                    for val in scatter_vals
                ]
                for item in wc:
                    if (item + "_wc") in step.input_scatter:
                        step.input_scatter.pop(step.input_scatter.index(item + "_wc"))
                rem_wc = [wc for wc in step.input_scatter if "_wc" in wc]
                rem_wc = [wc.replace("_wc", "") for wc in rem_wc]
                for key in scatter_keys:
                    val = scatter_vals[scatter_keys.index(key)]
                    if not any(get_wildcards(val, rem_wc)):
                        step.input_scatter.pop(step.input_scatter.index(key))

        self._input_scatter = scatters
