from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, cast

from pydantic import BaseModel

from hydroflows.methods.method import ExpandMethod, ReduceMethod

if TYPE_CHECKING:
    from hydroflows.rule import Rule


class JinjaSnakeRule:
    """ViewModel for a Rule to print in a Jinja Snakemake template."""

    def __init__(self, rule: "Rule"):
        self.rule = rule

    @property
    def name(self) -> str:
        """Get the name of the rule."""
        return self.rule.name

    @property
    def method_name(self) -> str:
        """Get the name of the method."""
        return self.rule.method.name

    @property
    def input(self) -> Dict[str, str]:
        """Get the rule input path parameters."""
        result = self.rule.input(mode="python", filter_types=Path)
        return {key: self._parse_variable(key, val) for key, val in result.items()}

    @property
    def output(self) -> Dict[str, str]:
        """Get the rule output path parameters."""
        result = self.rule.output(mode="python", filter_types=Path)
        return {key: self._parse_variable(key, val) for key, val in result.items()}

    @property
    def params(self) -> Dict[str, str]:
        """Get the rule parameters."""
        result = self.rule.params(
            mode="json",
            exclude_defaults=True,
            filter_keys=list(self.rule._kwargs.keys()),
        )
        return {key: self._parse_variable(key, val) for key, val in result.items()}

    @property
    def shell_args(self) -> Dict[str, str]:
        """Get the rule shell arguments."""
        return {
            key: self._parse_shell_variable(key) for key in self.rule._resolved_kwargs
        }

    def _parse_variable(self, key: str, val: Any) -> str:
        """Expand the wildcards in a string & resolve references."""
        # replace val with references to config or other rules
        kwargs = self.rule._kwargs
        str_val = str(val[0]) if isinstance(val, list) else str(val)
        expand_kwargs = []
        if isinstance(self.rule.method, (ReduceMethod, ExpandMethod)):
            for wc in self.rule.method.wildcards:  # expand/reduce wildcards
                if "{" + wc + "}" in str_val:
                    # NOTE wildcard values will be added by the workflow in upper case
                    expand_kwargs.append(f"{wc}={wc.upper()}")
            for wc in self.rule.wildcards:  # n:n wildcards
                # escape wildcard in the value which is not expanded
                if "{" + wc + "}" in str_val:
                    str_val = str_val.replace("{" + wc + "}", "{{" + wc + "}}")
        if expand_kwargs:
            # NOTE we assume product of all wildcards, this could be extended to also use zip
            expand_kwargs_str = ", ".join(expand_kwargs)
            v = f'expand("{str_val}", {expand_kwargs_str})'
        elif (
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
        elif isinstance(val, (Path, str)):
            # no references or wildcards, just add the value with quotes
            v = f'"{val}"'
        else:
            v = str(val)
        return v

    def _parse_shell_variable(self, key: str):
        """Parse the key value pair for the shell command."""
        # check if key is in input, output or params
        for c in ["input", "output", "params"]:
            comp = cast(BaseModel, getattr(self.rule.method, c))
            if key in comp.model_fields:
                value = f"{c}.{key}"
                return value
        raise ValueError(f"Key {key} not found in input, output or params.")
