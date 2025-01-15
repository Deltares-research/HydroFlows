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

    @property
    def rule_id(self) -> str:
        """Get the name of the rule."""
        return self.rule.rule_id

    @property
    def method_name(self) -> str:
        """Get the name of the method."""
        return self.rule.method.name

    @property
    def loop_depth(self) -> int:
        """Get loop depth of rule."""
        return self.rule._loop_depth

    @property
    def input(self) -> Dict[str, str]:
        """Get input dict for CWL step."""
        refs = self.rule.method.input.to_dict(filter_types=Path, return_refs=True)
        inputs = {}
        # Reduce wildcards determines type File[] vs type File
        reduce_wc = None
        if self.rule.wildcards["reduce"]:
            (reduce_wc,) = self.rule.wildcards["reduce"]

        for key, val in refs.items():
            inputs[key] = {}
            inputs[key]["type"] = "File"
            if isinstance(val, folderpath):
                inputs[key]["type"] = "Directory"
            # Set the source of the input (from prev rule, config)
            if "$config" in val:
                inputs[key]["source"] = val.split(".")[-1]
                if isinstance(self.rule.workflow.get_ref(val).value, folderpath):
                    inputs[key]["type"] = "Directory"
            if "$rules" in val:
                tmp = val.split(".")
                inputs[key]["source"] = f"{tmp[-3]}/{tmp[-1]}"
                if isinstance(self.rule.workflow.get_ref(val).value, folderpath):
                    inputs[key]["type"] = "Directory"
            # Set input type
            if reduce_wc and key in self.rule.wildcard_fields[reduce_wc]:
                inputs[key]["type"] += "[]"
        # Add params to inputs
        params = self.rule.method.params.to_dict(return_refs=True)
        for key, val in params.items():
            if isinstance(val, str) and "$" in val:
                inputs[key] = map_cwl_types(self.rule.method.params.to_dict()[key])
                inputs[key]["source"] = val.split(".")[-1]
            else:
                inputs[key] = map_cwl_types(val)
            inputs[key]["type"] += "?"

        return inputs

    @property
    def input_wildcards(self) -> str:
        """Get wildcards that need to be included in CWL step input."""
        if self.rule.wildcards["explode"]:
            wc = self.rule.wildcards["explode"]
            if len(wc) > 1:
                wc = [item + "_list" for item in wc]
            return wc
        else:
            return None

    @property
    def input_scatter(self) -> List[str]:
        """Get inputs for CWL step that are scattered over."""
        if self.rule.wildcards["reduce"]:
            return []
        ins = self.rule.method.input.to_dict()
        params = self.rule.method.params.to_dict()
        scatters = [key for key in ins.keys() if "{" in ins[key].as_posix()]
        scatters.extend([key for key in params.keys() if "{" in str(params[key])])
        if self.input_wildcards:
            scatters.extend(self.input_wildcards)
        return scatters

    @property
    def output(self) -> Dict[str, str]:
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
                for wc in self.input_wildcards:
                    outputs[key]["value"] = [
                        item.replace(("{" + f"{wc}" + "}"), f"$(input.{wc})")
                        for item in outputs[key]["value"]
                    ]
            if wc_expand and any(get_wildcards(val, wc_expand)):
                wc_dict = self.rule.method.expand_wildcards
                wc_values = list(product(*wc_dict.values()))
                outputs[key]["value"] = [
                    str(outputs[key]["value"]).format(**dict(zip(wc_expand, wc)))
                    for wc in wc_values
                ]
                outputs[key]["type"] += "[]"

        return outputs

    @property
    def params(self) -> Dict[str, str]:
        """Get rule params."""
        pars = self.rule.method.params.model_dump()
        results = {}
        for key, value in pars.items():
            if value is not None:
                results[key] = map_cwl_types(value)
        return results


class JinjaCWLWorkflow:
    """Class for exporting workflow to CWL."""

    def __init__(self, rules: List[JinjaCWLRule], start_loop_depth: int = 0):
        self.rules = rules
        self.workflow = rules[0].rule.workflow
        self.start_loop = start_loop_depth

    @property
    def input(self) -> Dict[str, str]:
        """Set CWL workflow inputs to be workflog.config + wildcards."""
        input_dict = {}

        for key, value in self.workflow.config:
            input_dict[key] = map_cwl_types(value)
        for wc in self.workflow.wildcards.names:
            input_dict[wc] = {
                "type": "string[]",
                "value": self.workflow.wildcards.get(wc),
            }

        return input_dict

    @property
    def output(self) -> Dict[str, str]:
        """Set CWL workflow outputs to be outputs of all rules."""
        output_dict = {}

        for rule in self.rules:
            for id, info in rule.output.items():
                output_dict[id] = {
                    "type": f"{info['type']}[]"
                    if rule.input_scatter
                    else f"{info['type']}",
                    "outputSource": f"{rule.rule_id}/{id}",
                }

        return output_dict

    @property
    def steps(self) -> List[Union[JinjaCWLRule, "JinjaCWLWorkflow"]]:
        """Set list of steps and subworkflows."""
        step_list = deepcopy(self.rules)

        sub_wf = [rule for rule in step_list if rule.loop_depth > self.start_loop]
        indices = [i for i, x in enumerate(step_list) if x in sub_wf]

        if sub_wf:
            step_list[indices[0] : indices[-1] + 1] = [
                JinjaCWLWorkflow(rules=sub_wf, start_loop_depth=self.start_loop + 1)
            ]

        return step_list

    @property
    def input_scatter(self) -> List[str]:
        """Set inputs which need to be scattered over."""
        return self.rules[0].input_scatter
