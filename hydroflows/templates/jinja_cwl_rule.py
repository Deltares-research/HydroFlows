import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union
from itertools import product

from hydroflows.utils.parsers import get_wildcards
from hydroflows.utils.cwl_utils import map_cwl_types
from hydroflows._typing import folderpath

if TYPE_CHECKING:
    from hydroflows.workflow.method import Method
    from hydroflows.workflow.rule import Rule

class JinjaCWLRule:

    def __init__(self, rule: "Rule"):
        self.rule = rule

    @property
    def rule_id(self) -> str:
        return self.rule.rule_id
    
    @property
    def method_name(self) -> str:
        return self.rule.method.name
    
    @property
    def input(self) -> Dict[str,str]:
        refs = self.rule.input.to_dict(
            filter_types=Path, return_refs=True
        )
        inputs = {}
        # Reduce wildcards determines type File[] vs type File
        reduce_wc = None
        if self.rule.wildcards["reduce"]:
            reduce_wc, = self.rule.wildcards["reduce"]

        for key, val in refs.items():
            inputs[key] = {}
            inputs[key]['type'] = "File"
            if isinstance(val, folderpath):
                inputs[key]['type'] = "Directory"
            # Set the source of the input (from prev rule, config)
            if "$config" in val:
                inputs[key]["source"] = val.split(".")[-1]
                if isinstance(self.rule.workflow.get_ref(val).value, folderpath):
                    inputs[key]['type'] = "Directory"
            if "$rules" in val:
                tmp = val.split(".")
                inputs[key]["source"] = f"{tmp[-3]}/{tmp[-1]}"
                if isinstance(self.rule.workflow.get_ref(val).value, folderpath):
                    inputs[key]['type'] = "Directory"
            # Set input type
            if reduce_wc and key in self.rule.wildcard_fields[reduce_wc]:
                inputs[key]["type"] += "[]"
        # Add params to inputs
        params = self.rule.method.params.to_dict(return_refs=True)
        for key, val in params.items():
            if isinstance(val,str) and "$" in val:
                inputs[key] = map_cwl_types(self.rule.params.to_dict()[key])
                inputs[key]["source"] = val.split(".")[-1]
            else:
                inputs[key] = map_cwl_types(val)
            inputs[key]['type'] += "?"

        return inputs

    @property
    def input_wildcards(self) -> str:
        explode_wc = None
        if self.rule.wildcards["explode"]:
            explode_wc, = self.rule.wildcards["explode"]

        return explode_wc

    @property
    def input_scatter(self) -> List[str]:
        if self.rule.wildcards["reduce"]:
            return []
        ins = self.rule.input.to_dict()
        scatters = [key for key in ins.keys() if "{" in ins[key].as_posix()]
        if self.input_wildcards:
            scatters.append(self.input_wildcards)
        return scatters 

    @property
    def output(self) -> Dict[str,str]:
        results = self.rule.output.to_dict(
            mode='python', filter_types=Path
        )
        outputs= {}
        wc_expand = self.rule.wildcards["expand"]
        for key,val in results.items():
            outputs[key] = {"value": [val.as_posix()]}
            if isinstance(val, folderpath):
                outputs[key]["type"] = "Directory"
                outputs[key]["value"] = [val.parent.as_posix()]
            else:
                outputs[key]["type"] = "File"
            if wc_expand and any(get_wildcards(val, wc_expand)):
                wc_dict = self.rule.method.expand_wildcards
                wc_values = list(product(*wc_dict.values()))
                outputs[key]['value'] = [str(val).format(**dict(zip(wc_expand, wc))) for wc in wc_values]
                outputs[key]['type'] += "[]"
            elif self.input_wildcards:
                wc = self.input_wildcards
                outputs[key]['value'] = [item.replace(("{"+f"{wc}"+"}"), f"$(input.{wc})") for item in outputs[key]['value']]

        return outputs
    
    @property
    def params(self) -> Dict[str, str]:
        pars = self.rule.method.params.model_dump()
        results = {}
        for key,value in pars.items():
            if value is not None:
                results[key] = map_cwl_types(value)
        return results
    