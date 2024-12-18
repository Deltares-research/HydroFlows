"""Submodule containing the Workflow class.

Which is the main class for defining workflows in hydroflows.
"""

import logging
import os
import tempfile
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional, Union

import yaml
from jinja2 import Environment, PackageLoader
from pydantic import BaseModel

from hydroflows import __version__
from hydroflows.templates.jinja_snake_rule import JinjaSnakeRule
from hydroflows.workflow.method import Method
from hydroflows.workflow.reference import Ref
from hydroflows.workflow.rule import Rule, Rules
from hydroflows.workflow.workflow_config import WorkflowConfig

logger = logging.getLogger(__name__)


class Workflow:
    """Workflow class."""

    def __init__(
        self,
        name="hydroflows",
        config: Optional[Union[Dict, WorkflowConfig]] = None,
        wildcards: Optional[Dict] = None,
    ) -> None:
        """Create a workflow instance.

        Workflow instances are validated and can be parsed to a workflow engine.

        Parameters
        ----------
        config : Dict, optional
            The configuration of the workflow, by default None.
        wildcards : Dict, optional
            The wildcard keys and values of the workflow, by default None.
        """
        if config is None:
            config = {}
        if wildcards is None:
            wildcards = {}

        self.name: str = str(name)
        self.config: WorkflowConfig = (
            WorkflowConfig(**config) if isinstance(config, dict) else config
        )
        self.wildcards: Wildcards = Wildcards(wildcards=wildcards)
        self.rules: Rules = Rules()

    def __repr__(self) -> str:
        rules_str = pformat(self.rules)
        wc_str = pformat(self.wildcards.to_dict())
        return f"Workflow(\nwildcards={wc_str}\nrules={rules_str}\n)"

    def add_rule(self, method: Method, rule_id: Optional[str] = None) -> None:
        """Add a rule to the workflow."""
        rule = Rule(method, self, rule_id)
        self.rules.set_rule(rule)

    def add_rule_from_kwargs(
        self, method: str, kwargs: Dict[str, str], rule_id: Optional[str] = None
    ) -> None:
        """Add a rule for method 'name' with keyword-arguments 'kwargs'.

        Parameters
        ----------
        method : str
            The name of the method.
        kwargs : Dict[str, str]
            The keyword arguments for the method.
        rule_id : str, optional
            The rule id, by default None.
        """
        # resolve references
        for key, value in kwargs.items():
            if isinstance(value, str) and value.startswith("$"):
                kwargs[key] = self.get_ref(value)
        # instantiate the method and add the rule
        m = Method.from_kwargs(name=str(method), **kwargs)
        self.add_rule(m, rule_id)

    def get_ref(self, ref: str) -> Ref:
        """Get a cross-reference to previously set rule parameters or workflow config."""
        return Ref(ref, self)

    @classmethod
    def from_yaml(cls, file: str) -> "Workflow":
        """Load a workflow from a yaml file."""
        # Load the yaml file
        with open(file, "r") as f:
            yml_dict = yaml.safe_load(f)

        # Create the workflow instance
        rules: List[Dict] = yml_dict.pop("rules")
        workflow: Workflow = cls(**yml_dict)

        # Add the rules to the workflow
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ValueError(f"Rule {i+1} invalid: not a dictionary.")
            if "method" not in rule.keys():
                raise ValueError(f"Rule {i+1} invalid: 'method' name missing.")
            workflow.add_rule_from_kwargs(**rule)
        return workflow

    def to_snakemake(
        self,
        snakefile: Path,
        dryrun: bool = False,
    ) -> None:
        """Save the workflow to a snakemake workflow.

        Parameters
        ----------
        snakefile : Path
            The path to the snakefile.
        dryrun : bool, optional
            Run the workflow in dryrun mode, by default False.
        run_env : Literal["shell", "script"], optional
            The environment in which to run the methods, by default "shell".
        """
        snakefile = Path(snakefile).resolve()
        configfile = snakefile.with_suffix(".config.yml")
        template_env = Environment(
            loader=PackageLoader("hydroflows"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = template_env.get_template("workflow.smk.jinja")
        configfile = snakefile.parent / snakefile.with_suffix(".config.yml").name
        snake_rules = [JinjaSnakeRule(r) for r in self.rules]
        _str = template.render(
            version=__version__,
            configfile=configfile.name,
            rules=snake_rules,
            wildcards=self.wildcards.wildcards,
            dryrun=dryrun,
        )
        # Small check for the parent directory
        snakefile.parent.mkdir(parents=True, exist_ok=True)
        # After that write
        with open(snakefile, "w") as f:
            f.write(_str)
        with open(snakefile.parent / configfile, "w") as f:
            yaml.dump(self.config.to_dict(mode="json", posix_path=True), f)

    def to_yaml(self, file: str) -> None:
        """Save the workflow to a yaml file."""
        yml_dict = {
            "config": self.config.to_dict(mode="json"),
            "wildcards": self.wildcards.to_dict(),
            "rules": [r.to_dict() for r in self.rules],
        }
        with open(file, "w") as f:
            yaml.dump(yml_dict, f, sort_keys=False)

    def run(
        self,
        max_workers=1,
        dryrun: bool = False,
        missing_file_error: bool = False,
        tmpdir: Optional[Path] = None,
    ) -> None:
        """Run the workflow.

        Parameters
        ----------
        max_workers : int, optional
            The maximum number of workers, by default 1.
            Only used when dryrun is False.
        dryrun : bool, optional
            Run the workflow in dryrun mode, by default False.
        missing_file_error : bool, optional
            Raise an error when a file is missing, by default False.
            This only works when dryrun is True.
        tmpdir : Optional[Path], optional
            The temporary directory to run the dryrun in, by default None.
        """
        # do dryrun in a tmp directory
        if dryrun:
            curdir = Path.cwd()
            if tmpdir is None:
                tmpdir = Path(tempfile.mkdtemp(prefix="hydroflows_"))
            Path(tmpdir).mkdir(parents=True, exist_ok=True)
            os.chdir(tmpdir)
            logger.info("Running dryrun in %s", tmpdir)

        nrules = len(self.rules)
        for i, rule in enumerate(self.rules):
            logger.info("Rule %d/%d: %s", i + 1, nrules, rule.rule_id)
            rule.run(
                dryrun=dryrun,
                max_workers=max_workers,
                missing_file_error=missing_file_error,
            )

        if dryrun:
            os.chdir(curdir)

    @property
    def _output_path_refs(self) -> Dict[str, str]:
        """Retrieve output path references of all rules in the workflow.

        Returns
        -------
        Dict[str, str]
            Dictionary containing the output path as the key and the reference as the value
        """
        output_paths = {}
        for rule in self.rules:
            if not rule:
                continue
            for key, value in rule.output:
                if isinstance(value, Path):
                    value = value.as_posix()
                else:
                    logger.debug(
                        f"{rule.rule_id}.output.{key} is not a Path object (but {type(value)})"
                    )
                    continue
                output_paths[value] = f"$rules.{rule.rule_id}.output.{key}"
        return output_paths


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
        key = str(key).lower()
        self.wildcards.update({key: values})

    def get(self, key: str) -> List[str]:
        """Get the values of a wildcard."""
        key = str(key).lower()
        return self.wildcards[key]
