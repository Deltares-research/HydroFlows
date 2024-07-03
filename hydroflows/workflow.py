"""Submodule containing the Workflow class.

Which is the main class for defining workflows in hydroflows.
"""

from pathlib import Path
from pprint import pformat
from typing import Any, Dict, List

import yaml
from jinja2 import Environment, PackageLoader
from pydantic import BaseModel

from hydroflows import __version__
from hydroflows.rule import Rule
from hydroflows.templates._jinja_snake_rule import JinjaSnakeRule


class Wildcards(BaseModel):
    """Wildcards class.

    This class is used to define the wildcards for the workflow.
    """

    wildcards: Dict[str, List[str]] = {}
    """List of wildcard keys and values."""

    @property
    def names(self) -> List[str]:
        """Get the names of the wildcards."""
        return list(self.wildcards.keys())

    @property
    def values(self) -> List[List]:
        """Get the values of the wildcards."""
        return list(self.wildcards.values())

    def to_dict(self) -> Dict[str, List]:
        """Convert the wildcards to a dictionary of names and values."""
        return self.model_dump()["wildcards"]

    def set(self, key: str, values: List[str]):
        """Add a wildcard."""
        self.wildcards.update({key: values})

    def get(self, key: str) -> List[str]:
        """Get the values of a wildcard."""
        return self.wildcards[key]


class Workflow:
    """Workflow class."""

    def __init__(
        self,
        config: Dict,
        rules: List[Dict],
        results: List = None,
        wildcards: Dict[str, List[str]] = None,
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
        if wildcards is None:
            wildcards = {}
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

        # TODO check if all wildcards in rules are in self.wildcards with values
        self._check_wildcards()

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
                value = get_nested_value_from_dict(self.config, ref_keys[1:], reference)
            case "$rules":
                if not len(ref_keys) >= 4:
                    raise ValueError(
                        f"Invalid rule reference: {value}. "
                        "A rule reference should be in the form $rules.<rule_name>.<rule_component>.<key>, "
                        "where <rule_component> is one of input, output or params."
                    )
                rule_dict = self.get_rule(ref_keys[1]).to_dict()
                value = get_nested_value_from_dict(rule_dict, ref_keys[2:], reference)
            case _:
                raise ValueError(
                    f"Invalid reference: {reference}. References should start with $config or $rules."
                )
        return value

    def _check_wildcards(self) -> None:
        """Check if all wildcards in rules are in self.wildcards with values."""
        # TODO: implement
        pass

    @classmethod
    def from_yaml(cls, file: str):
        """Load a workflow from a yaml file."""
        # Load the yaml file
        with open(file, "r") as f:
            yml_dict = yaml.safe_load(f)
        return cls(**yml_dict)

    def to_snakemake(self, snakefile: Path):
        """Convert the workflow to a snakemake workflow."""
        template_env = Environment(
            loader=PackageLoader("hydroflows"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = template_env.get_template("workflow.smk.jinja")
        configfile = Path(snakefile).with_suffix(".config.yml").name
        _str = template.render(
            version=__version__,
            configfile=configfile,
            rules=[JinjaSnakeRule(r) for r in self.rules],
            wildcards=self.wildcards.wildcards,
            rules_all=self._snake_rule_all(),
        )
        with open(snakefile, "w") as f:
            f.write(_str)
        with open(configfile, "w") as f:
            yaml.dump(self.config, f)

    def _snake_rule_all(self) -> List[str]:
        rule_all = []
        for ref in self.results:
            if not ref.startswith("$rules"):
                raise ValueError(
                    f"Invalid result reference: {ref}. References should start with $rules."
                )
            val = self._resolve_references(ref)
            expand_kwargs = []
            for wc in self.wildcards.names:
                if "{" + wc + "}" in str(val):
                    # NOTE wildcard values will be added by the workflow in upper case
                    expand_kwargs.append(f"{wc}={wc.upper()}")
            if expand_kwargs:
                # NOTE we assume product of all wildcards, this could be extended to also use zip
                expand_kwargs_str = ", ".join(expand_kwargs)
                v = f'expand("{val}", {expand_kwargs_str})'
            else:
                # no references or wildcards, just add the value with quotes
                v = f'"{val}"'
            rule_all.append(v)
        return rule_all

    def run(self):
        """Run the workflow."""
        nrules = len(self.rules)
        for i, rule in enumerate(self.rules):
            print(f">> Rule {i+1}/{nrules}: {rule.name}")
            rule.run()


def get_nested_value_from_dict(d: dict, keys: list, full_reference: str = None) -> Any:
    """Get nested value from dictionary."""
    if full_reference is None:
        full_reference = ".".join(keys)
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            raise KeyError(f"Key not found: {full_reference}")
    return d
