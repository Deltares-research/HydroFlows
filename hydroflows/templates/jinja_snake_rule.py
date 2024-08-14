from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Union

if TYPE_CHECKING:
    from hydroflows.workflow.method import Method
    from hydroflows.workflow.rule import Rule


class JinjaSnakeRule:
    """ViewModel for a Rule to print in a Jinja Snakemake template."""

    def __init__(self, rule: "Rule"):
        self.rule = rule

    @property
    def method(self) -> "Method":
        """Get the rule method instance."""
        return self.rule.method

    @property
    def rule_id(self) -> str:
        """Get the name of the rule."""
        return self.rule.rule_id

    @property
    def method_name(self) -> str:
        """Get the name of the method."""
        return self.method.name

    @property
    def input(self) -> Dict[str, str]:
        """Get the rule input path parameters."""
        result = self.method.input.to_dict(
            mode="python", filter_types=Path, return_refs=True
        )
        wildcards = self.rule.wildcards["reduce"]
        for key, val in result.items():
            # get the original value instead of the reference
            org_val = getattr(self.method.input, key)
            if wildcards and any("{" + wc + "}" in str(org_val) for wc in wildcards):
                result[key] = self._expand_variable(org_val, wildcards)
            else:
                result[key] = self._parse_variable(val)
        return result

    @property
    def output(self) -> Dict[str, str]:
        """Get the rule output path parameters."""
        result = self.method.output.to_dict(mode="python", filter_types=Path)
        wildcards = self.rule.wildcards["expand"]
        for key, val in result.items():
            if wildcards and any("{" + wc + "}" in str(val) for wc in wildcards):
                result[key] = self._expand_variable(val, wildcards)
            else:
                result[key] = self._parse_variable(val)
        return result

    @property
    def params(self) -> Dict[str, str]:
        """Get the rule parameters."""
        result = self.method.params.to_dict(
            mode="python", exclude_defaults=True, return_refs=True
        )
        return {key: self._parse_variable(val) for key, val in result.items()}

    @property
    def rule_all_input(self) -> Dict[str, str]:
        """Get the rule all input (output paths with expand)."""
        result = self.method.output.to_dict(mode="python", filter_types=Path)
        wildcards = self.rule.workflow.wildcards.names
        for key, val in result.items():
            result[key] = self._expand_variable(val, wildcards)
        return result

    @property
    def shell_args(self) -> Dict[str, str]:
        """Get the rule shell arguments."""
        return {key: self._parse_shell_variable(key) for key in self.method.kwargs}

    def _expand_variable(self, val: Union[str, Path], wildcards: List) -> Any:
        if isinstance(val, Path):
            val = val.as_posix()
        val = str(val)
        expand_lst = []
        for wc in wildcards:
            if "{" + wc + "}" in val:
                expand_lst.append(f"{wc}={wc.upper()}")
        for wc in set(self.rule.wildcards["explode"]) - set(wildcards):
            if "{" + wc + "}" in val:
                # escape wildcard in the value which is not expanded
                val = val.replace("{" + wc + "}", "{{" + wc + "}}")
        if len(expand_lst) == 0:
            raise ValueError(f"No wildcards found in {val}")
        expand_str = ", ".join(expand_lst)
        val = f'expand("{val}", {expand_str})'
        return val

    def _parse_config_reference(self, val: str) -> str:
        """Parse the config reference to snakemake format."""
        dict_keys = val.split(".")[1:]
        return 'config["' + '"]["'.join(dict_keys) + '"]'

    def _parse_variable(self, val: Any) -> str:
        """Expand the wildcards and parse references to snakemake format."""
        if isinstance(val, Path):
            val = f'"{val.as_posix()}"'
        elif isinstance(val, str) and val.startswith("config."):
            val = self._parse_config_reference(val)
        elif isinstance(val, str) and val.startswith("rules."):
            pass  # already in snakemake format
        elif isinstance(val, str):
            val = f'"{val}"'
        return str(val)

    def _parse_shell_variable(self, key: str) -> str:
        """Parse the key value pair for the shell command."""
        # check if key is in input, output or params
        for c in self.method.dict:
            if key in self.method.dict[c]:
                return f"{c}.{key}"
        raise ValueError(f"Key {key} not found in input, output or params.")
