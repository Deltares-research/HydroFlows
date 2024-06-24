"""Submodule containing the Workflow class.

Which is the main class for defining workflows in hydroflows.
"""

from pathlib import Path
from pprint import pformat
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, field_validator

from hydroflows import __version__
from hydroflows.rule import Rule


class Wildcard(BaseModel):
    """Wildcards class.

    This class is used to define the wildcards for the workflow.
    """

    name: str
    """Name of the wildcard."""

    values: Optional[List[str]] = None
    """Values of the wildcard."""

    ref: Optional[str] = None
    """Reference of the wildcard to a rule output."""


class Wildcards(BaseModel):
    """Wildcards class.

    This class is used to define the wildcards for the workflow.
    """

    wildcards: List[Wildcard]
    """List of wildcards."""

    @field_validator("wildcards", mode="before")
    @classmethod
    def _set_wildcards(cls, value: Any) -> List[Wildcard]:
        # if list of dictionaries, convert to list of Wildcard
        if isinstance(value, list) and all(isinstance(f, dict) for f in value):
            return [Wildcard(**wc) for wc in value]
        return value

    @property
    def names(self) -> List[str]:
        """Get the names of the wildcards."""
        return [wildcard.name for wildcard in self.wildcards]

    @property
    def values(self) -> List[List]:
        """Get the values of the wildcards."""
        return [wildcard.values for wildcard in self.wildcards]

    def to_dict(self) -> Dict[str, List]:
        """Convert the wildcards to a dictionary of names and values."""
        return {k: v for k, v in zip(self.names, self.values)}

    def _snake_wildcards(self) -> str:
        wc_str = ""
        for wildcard in self.wildcards:
            assert wildcard.values is not None
            wc_str += f"{wildcard.name.upper()} = {wildcard.values}\n"
        return wc_str

    def get_wildcard(self, name: str) -> Wildcard:
        """Get a wildcard from the wildcards."""
        wildcard = next(
            (wildcard for wildcard in self.wildcards if wildcard.name == name), None
        )
        if wildcard is None:
            raise ValueError(f"Wildcard {name} not found in wildcards.")
        return wildcard


class Workflow:
    """Workflow class."""

    def __init__(
        self,
        config: Dict,
        rules: List[Dict],
        results: List = None,
        wildcards: List[Dict] = None,
    ) -> None:
        """Create a workflow instance.

        Workflow instances are validated and can be parsed to a workflow engine.

        Parameters
        ----------
        config : Dict
            The configuration of the workflow.
        rules : List
            The rules of the workflow.
        results : List
            The results of the workflow.
        wildcards : List[Dict], optional
            The wildcards of the workflow, by default None.
        """
        self.config: Dict = config  # TODO: create Config pydantic model
        self.wildcards: Wildcards = Wildcards(wildcards=wildcards)
        self.rules: List[Rule] = []
        self.results: List[str] = results

        # initialize rules, this will:
        # - validate if rule kwargs are correct
        # - create rule outputs which can be used in subsequent rules
        #   and are required to parse to a workflow engine
        for rule in rules:
            self.add_rule(**rule)

        # after all rules are initialized, wildcards that are output of rules can be resolved
        self._resolve_wildcards()

        # if results are not provided, use the output of the last rule
        if self.results is None:
            out_rule = self.rules[-1].name
            out_keys = self.rules[-1].output(filter_types=Path).keys()
            self.results = [f"$rules.{out_rule}.output.{key}" for key in out_keys]

    def __repr__(self) -> str:
        rules_str = pformat(self.rules)
        wc_str = pformat(self.wildcards.to_dict())
        return f"Workflow(\nwildcards={wc_str}\nrules={rules_str}\n)"

    def add_rule(self, method: str, kwargs: dict):
        """Add a rule to the workflow."""
        rule = Rule(method_name=method, kwargs=kwargs, workflow=self)
        self.rules.append(rule)

    def get_rule(self, name: str) -> Rule:
        """Get a rule from the workflow."""
        rule = next((rule for rule in self.rules if rule.name == name), None)
        if rule is None:
            raise ValueError(f"Rule {name} not found in workflow.")
        return rule

    def _resolve_references(self, reference: str) -> Any:
        """Resolve references to config and rules.

        References are start with either $config or $rules
        and are dot separated strings to access nested values.

        For instance $config.region.geom would resolve to
        the value of config["region"]["geom"].

        Parameters
        ----------
        reference : str
            Reference to resolve.
        """
        ref_keys = reference.split(".")
        match ref_keys[0]:
            case "$config":
                value = get_nested_value_from_dict(self.config, ref_keys[1:])
            case "$rules":
                if not len(ref_keys) >= 4:
                    raise ValueError(
                        f"Invalid rule reference: {value}. "
                        "A rule reference should be in the form $rules.<rule_name>.<rule_component>.<key>, "
                        "where <rule_component> is one of input, output or params."
                    )
                rule_dict = self.get_rule(ref_keys[1]).to_dict()
                value = get_nested_value_from_dict(rule_dict, ref_keys[2:])
            case _:
                raise ValueError(
                    f"Invalid reference: {reference}. References should start with $config or $rules."
                )
        return value

    def _resolve_wildcards(self) -> None:
        """Resolve wildcards with references to rules."""
        for wildcard in self.wildcards.wildcards:
            if wildcard.ref is not None:
                wildcard.values = self._resolve_references(wildcard.ref)

    @classmethod
    def from_yaml(cls, file: str):
        """Load a workflow from a yaml file."""
        # Load the yaml file
        with open(file, "r") as f:
            yml_dict = yaml.safe_load(f)
        return cls(**yml_dict)

    def to_snakemake(self, snakefile: Path):
        """Convert the workflow to a snakemake workflow."""
        configfile = Path(snakefile).with_suffix(".config.yml")
        _str = f"# This file was generated by hydroflows version {__version__}\n\n"
        _str += f'configfile: "{configfile}"\n\n'
        _str += self.wildcards._snake_wildcards() + "\n\n"
        _str += self._snake_rule_all() + "\n\n"
        _str += "\n".join(rule.to_str("snakemake") for rule in self.rules)
        with open(snakefile, "w") as f:
            f.write(_str)
        with open(configfile, "w") as f:
            yaml.dump(self.config, f)

    def _snake_rule_all(self) -> str:
        rule_all = "rule all:\n    input:\n"
        for ref in self.results:
            if not ref.startswith("$rules"):
                raise ValueError(
                    f"Invalid result reference: {ref}. References should start with $rules."
                )
            key = ref.split(".")[-1]
            value = self._resolve_references(ref)
            rule = self.get_rule(ref.split(".")[1])
            result = rule._parse_snake_key_value(key, value, "output")
            rule_all += f"        {result},\n"
        return rule_all

    def run(self):
        """Run the workflow."""
        nrules = len(self.rules)
        for i, rule in enumerate(self.rules):
            print(f">> Rule {rule.name} ({i+1}/{nrules})")
            rule.run()


def get_nested_value_from_dict(d: dict, keys: list) -> Any:
    """Get nested value from dictionary."""
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            key_str = ".".join(keys)
            raise KeyError(f"Key not found: {key_str}")
    return d
