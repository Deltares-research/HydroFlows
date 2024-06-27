import typing
from typing import cast

from jinja2 import Environment
from pydantic import BaseModel

from hydroflows.methods.method import ExpandMethod

if typing.TYPE_CHECKING:
    from hydroflows.rule import Rule


def setup_rule_env(env: Environment, rule: "Rule"):

    def expand(val, key):
        """Expand the wildcards in a string."""
        # replace val with references to config or other rules
        kwargs = rule._kwargs
        if key in kwargs and kwargs[key].startswith("$"):
            if kwargs[key].startswith("$config"):
                # resolve to python dict-like access
                dict_keys = kwargs[key].split(".")[1:]
                v = 'config["' + '"]["'.join(dict_keys) + '"]'
            elif kwargs[key].startswith("$rules"):
                v = f"{kwargs[key][1:]}"
        else:
            expand_kwargs = []
            if isinstance(rule.method, ExpandMethod):
                for wc in rule.method.expand_values.keys():
                    if "{" + wc + "}" in str(val):
                        # NOTE wildcard values will be added by the workflow in upper case
                        expand_kwargs.append(f"{wc}={wc.upper()}")
            if expand_kwargs:
                for wc in rule.wildcards:
                    if "{" + wc + "}" in str(val):
                        # escape the wildcard in the value
                        val = str(val).replace("{" + wc + "}", "{{" + wc + "}}")
                # NOTE we assume product of all wildcards, this could be extended to also use zip
                expand_kwargs_str = ", ".join(expand_kwargs)
                v = f'expand("{val}", {expand_kwargs_str})'
            else:
                # no references or wildcards, just add the value with quotes
                v = f'"{val}"'
        return v
    
    def shell_value(key):
        """Parse the key value pair for the shell command."""
        # check if key is in input, output or params
        for c in ["input", "output", "params"]:
            comp = cast(BaseModel, getattr(rule.method, c))
            if key in comp.model_fields:
                value = f"{c}.{key}"
                return '"{' + value + '}"'
        raise ValueError(f"Key {key} not found in input, output or params.")

    env.filters["expand"] = expand
    env.filters["shell_value"] = shell_value
