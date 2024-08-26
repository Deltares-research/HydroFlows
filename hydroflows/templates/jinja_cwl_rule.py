from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union

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
        results = self.rule.input(
            mode="python", filter_types=Path
        )
        return results
    
    @property
    def output(self) -> Dict[str,str]:
        results = self.rule.output(
            mode='python', filter_types=Path
        )
        outputs= {}
        for key,val in results.items():
            outputs[key] = {"value": val}
            if "{"  in str(val):
                outputs[key]['type'] = "File[]"
            else:
                outputs[key]['type'] = "File"
        return results
    
    @property
    def params(self) -> Dict[str, str]:
        pars = self.rule.method.params.model_dump()
        results = {}
        for key,value in pars.items():
            if value is not None:
                results[key] = _map_type_to_cwl(value)
        return results
    

def _map_type_to_cwl(input):
    out = {}
    match input:
        case bool():
            out['type']='string'
            out['value']=f"\"{str(input)}\""
        case Path():
            if not input.exists():
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
            out['type']='string'
            out['value']=f"\"{str(input)}\""
        case float():
            out['type']='float'
            out['value']=input
        case int():
            out['type']='float'
            out['value']=input
    return out   