from pathlib import Path
from typing import TYPE_CHECKING, Dict, cast

from pydantic import BaseModel

from hydroflows.methods.method import ExpandMethod

if TYPE_CHECKING:
    from hydroflows.rule import Rule


class JinjaSnakeRule:
    """ViewModel for a Rule to print in a Jinja Snakemake template."""

    def __init__(self, rule: "Rule"):
        self.rule = rule

    @property
    def name(self) -> str:
        return self.rule.name

    @property
    def method_name(self) -> str:
        return self.rule.method.name

    @property
    def input(self) -> Dict[str, str]:
        result = self.rule.input(mode="python", filter_types=Path)
        return {key: self._expand_variable(key, val) for key, val in result.items()}

    @property
    def output(self) -> Dict[str, str]:
        result = self.rule.output(mode="python", filter_types=Path)
        return {key: self._expand_variable(key, val) for key, val in result.items()}

    @property
    def params(self) -> Dict[str, str]:
        result = self.rule.params(
            mode="json",
            exclude_defaults=True,
            filter_keys=list(self.rule._kwargs.keys()),
        )
        return {key: self._expand_variable(key, val) for key, val in result.items()}

    @property
    def shell_args(self) -> Dict[str, str]:
        return {
            key: self._expand_shell_variable(key) for key in self.rule._resolved_kwargs
        }

    def _expand_variable(self, key: str, val: str):
        """Expand the wildcards in a string."""
        # replace val with references to config or other rules
        kwargs = self.rule._kwargs
        if (
            key in kwargs
            and isinstance(kwargs[key], str)
            and kwargs[key].startswith("$")
        ):
            if kwargs[key].startswith("$config"):
                # resolve to python dict-like access
                dict_keys = kwargs[key].split(".")[1:]
                v = 'config["' + '"]["'.join(dict_keys) + '"]'
            elif kwargs[key].startswith("$rules"):
                v = f"{kwargs[key][1:]}"
        else:
            expand_kwargs = []
            if isinstance(self.rule.method, ExpandMethod):
                for wc in self.rule.method.expand_values.keys():
                    if "{" + wc + "}" in str(val):
                        # NOTE wildcard values will be added by the workflow in upper case
                        expand_kwargs.append(f"{wc}={wc.upper()}")
            if expand_kwargs:
                for wc in self.rule.wildcards:
                    if "{" + wc + "}" in str(val):
                        # escape the wildcard in the value
                        val = str(val).replace("{" + wc + "}", "{{" + wc + "}}")
                # NOTE we assume product of all wildcards, this could be extended to also use zip
                expand_kwargs_str = ", ".join(expand_kwargs)
                v = f'expand("{val}", {expand_kwargs_str})'
            elif isinstance(val, (Path, str)):
                # no references or wildcards, just add the value with quotes
                v = f'"{val}"'
            else:
                v = str(val)
        return v

    def _expand_shell_variable(self, key: str):
        """Parse the key value pair for the shell command."""
        # check if key is in input, output or params
        for c in ["input", "output", "params"]:
            comp = cast(BaseModel, getattr(self.rule.method, c))
            if key in comp.model_fields:
                value = f"{c}.{key}"
                return value
        raise ValueError(f"Key {key} not found in input, output or params.")
