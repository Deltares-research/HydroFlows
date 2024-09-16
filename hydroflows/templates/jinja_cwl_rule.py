import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union
from itertools import product

from hydroflows.utils.parsers import get_wildcards

if TYPE_CHECKING:
    from hydroflows.workflow.method import Method
    from hydroflows.workflow.rule import Rule

class JinjaCWLRule:

    def __init__(self, rule: "Rule"):
        self.rule = rule

    @property
    def name(self) -> str:
        return self.rule.name
    
    @property
    def method_name(self) -> str:
        return self.rule.method.name
    
    @property
    def input(self) -> Dict[str,str]:
        results = self.rule.input.to_dict(
            mode="python", filter_types=Path
        )
        inputs = {}
        reduce_wc = None
        if self.rule.wildcards["reduce"]:
            reduce_wc, = self.rule.wildcards["reduce"]
        for key, val in results.items():
            inputs[key] = {"value": val}
            if reduce_wc and key in self.rule.wildcard_fields[reduce_wc]:
                inputs[key]["type"] = "File[]"
            else:
                inputs[key]["type"] = "File"
        return inputs
    
    @property
    def input_wildcards(self) -> Dict[str,str]:
        explode_wc = None
        if self.rule.wildcards["explode"]:
            explode_wc, = self.rule.wildcards["explode"]

        return explode_wc

    @property
    def output(self) -> Dict[str,str]:
        results = self.rule.output.to_dict(
            mode='python', filter_types=Path
        )
        outputs= {}
        wc_expand = self.rule.wildcards["expand"]
        # wc_explode = self.rule.wildcards["explode"]
        for key,val in results.items():
            outputs[key] = {"value": [val.as_posix()]}
            if wc_expand and any(get_wildcards(val, wc_expand)):
                # wc_dict = self.rule._workflow_ref().wildcards.to_dict()
                wc_dict = self.rule.method.expand_wildcards
                wc_values = list(product(*wc_dict.values()))
                outputs[key]['value'] = [str(val).format(**dict(zip(wc_dict.keys(), wc))) for wc in wc_values]
                outputs[key]['type'] = "File[]"
                # This is where we want to end up, but the corresponding outputEval needs thinking
                # outputs[key]['value'] = re.sub(r"\{.*?\}", "*", str(val))
            # elif wc_explode and any(get_wildcards(val, wc_explode)):
            elif self.input_wildcards:
                wc = self.input_wildcards
                outputs[key]['value'] = [item.replace(("{"+f"{wc}"+"}"), f"$(input.{wc})") for item in outputs[key]['value']]
                # outputs[key]['value'] = outputs[key]['value'].replace(("{"+f"{wc_explode}"+"}"), f"$({wc_explode})")
                outputs[key]['type'] = "File"
            else:
                outputs[key]['type'] = "File"
        return outputs
    
    @property
    def params(self) -> Dict[str, str]:
        pars = self.rule.method.params.model_dump()
        results = {}
        for key,value in pars.items():
            if value is not None:
                results[key] = _map_param_to_cwl(value)
        return results
    

def _map_param_to_cwl(input):
    out = {}
    match input:
        case bool():
            out['type']='string'
            out['value']=f"\"{str(input)}\""
        case Path():
            if not input.suffix:
                out['type']="string"
                out['value']=f"\"{input.as_posix()}\""
            else:
                indent = 3*"    "
                out['type']='File'
                out['value']=f"\n{indent}Class: File\n{indent}Path: \"{input.as_posix()}\""
        case str():
            out['type']='string'
            out['value']=f"\"{input}\""
        case list():
            if all(isinstance(item, str) for item in input):
                out["type"] = "string[]"
                out["value"] = [f"\"{item}\"" for item in input]
            elif all(isinstance(item, float) for item in input):
                out["type"] = "float[]"
                out["value"] = input
            elif all(isinstance(item, int) for item in input):
                out["type"] = "int[]"
                out["value"] = input
            else:
                raise TypeError("No lists with mixed typed elements allowed!")
            out["separator"] = "\", \""
        case float():
            out['type']='float'
            out['value']=input
        case int():
            out['type']='float'
            out['value']=input
        case _:
            out['type']='string'
    return out   