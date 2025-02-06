"""Submodule containing the Workflow class.

Which is the main class for defining workflows in hydroflows.
"""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional, Union

import yaml
from jinja2 import Environment, PackageLoader
from pydantic import BaseModel

from hydroflows import __version__
from hydroflows.templates.jinja_cwl_rule import JinjaCWLRule, JinjaCWLWorkflow
from hydroflows.templates.jinja_snake_rule import JinjaSnakeRule
from hydroflows.utils.cwl_utils import map_cwl_types
from hydroflows.utils.parsers import get_wildcards
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
        root: Optional[Path] = None,
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

        if root is not None:
            self.root = root

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

    @property
    def root(self) -> Path:
        """Get the root of the workflow."""
        if not hasattr(self, "_root"):
            return Path.cwd()
        return self._root

    @root.setter
    def root(self, root: Path) -> None:
        """Set the root of the workflow and create the directory if it does not yet exist."""
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

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
        snakefile: str = "Snakefile",
        dryrun: bool = False,
    ) -> None:
        """Save the workflow to a snakemake workflow.

        Parameters
        ----------
        snakefile : Path
            The snakefile filename, by default "Snakefile".
        dryrun : bool, optional
            Run the workflow in dryrun mode, by default False.
        """
        # set paths and creat directory
        snake_path = Path(self.root, snakefile).resolve()
        config_path = Path(snake_path.parent, f"{snake_path.stem}.config.yml").resolve()
        # render the snakefile template
        template_env = Environment(
            loader=PackageLoader("hydroflows"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = template_env.get_template("workflow.smk.jinja")
        snake_rules = [JinjaSnakeRule(r) for r in self.rules]
        _str = template.render(
            version=__version__,
            configfile=config_path.name,
            rules=snake_rules,
            wildcards=self.wildcards.wildcards,
            dryrun=dryrun,
        )
        # write the snakefile and config file
        with open(snake_path, "w") as f:
            f.write(_str)
        with open(config_path, "w") as f:
            yaml.dump(self.config.to_dict(mode="json", posix_path=True), f)

    def to_cwl(
        self,
        cwlfile: Path,
        dryrun: bool = False,
    ) -> None:
        """Save the workflow to a CWL workflow.

        Parameters
        ----------
        cwlfile : Path
            Path to the CWL workflow file. CWL files for individual methods will be created in the subfolder <cwlfile>/cwl.
        dryrun : bool, optional
            Run the workflow in dryrun mode, by default False
        """
        cwlfile = Path(cwlfile).resolve()
        configfile = cwlfile.with_suffix(".config.yml")
        # Make sure all necessary folders exist
        if not (cwlfile.parent / "cwl").exists():
            (cwlfile.parent / "cwl").mkdir(parents=True)

        template_env = Environment(
            loader=PackageLoader("hydroflows"), trim_blocks=True, lstrip_blocks=True
        )
        template_workflow = template_env.get_template("workflow.cwl.jinja")
        template_rule = template_env.get_template("rule.cwl.jinja")

        # Write CWL files for the methods
        for rule in self.rules:
            _str = template_rule.render(version=__version__, rule=JinjaCWLRule(rule))
            with open(f"{cwlfile.parent}/cwl/{rule.method.name}.cwl", "w") as f:
                f.write(_str)

        # Set workflow config as inputs and evaluate wildcards
        input_dict = {}
        for key, value in self.config:
            if isinstance(value, Path) and "{" in value.as_posix():
                wildcards = get_wildcards(value)
                for wc in wildcards:
                    new_val = [
                        value.as_posix().format(**dict(zip([wc], [wc_val])))
                        for wc_val in self.wildcards.get(wc)
                    ]
                    new_val = [Path(val) for val in new_val]
            elif isinstance(value, str) and "{" in value:
                wildcards = get_wildcards(value)
                for wc in wildcards:
                    new_val = [
                        value.format(**dict(zip([wc], [wc_val])))
                        for wc_val in self.wildcards.get(wc)
                    ]
            else:
                new_val = value

            input_dict[key] = map_cwl_types(new_val)
        for wc in self.wildcards.names:
            input_dict[wc + "_wc"] = {
                "type": "string[]",
                "value": self.wildcards.get(wc),
            }
        if dryrun:
            input_dict["dryrun"] = {"type": "boolean", "value": dryrun}
            input_dict["touch_output"] = {"type": "boolean", "value": True}

        # Write CWL file for workflow
        cwl_workflow = JinjaCWLWorkflow([JinjaCWLRule(r) for r in self.rules])

        _str = template_workflow.render(
            version=__version__,
            inputs=input_dict,
            workflow=cwl_workflow,
            dryrun=dryrun,
        )
        with open(cwlfile, "w") as f:
            f.write(_str)

        # Write CWL config file
        config = {key: value["value"] for key, value in input_dict.items()}
        with open(configfile, "w") as f:
            yaml.dump(config, f)

        # For dryrun, touch missing input files
        if dryrun:
            for _, info in config.items():
                if isinstance(info, dict):
                    fn = Path(info["path"])
                    if not fn.is_absolute():
                        fn = self.root / fn
                    if not fn.exists():
                        fn.parent.mkdir(parents=True)
                        fn.touch()
                elif isinstance(info, list) and all(isinstance(x, dict) for x in info):
                    for x in info:
                        fn = Path(x["path"])
                        if not fn.is_absolute():
                            fn = self.root / fn
                        if not fn.exists():
                            fn.parent.mkdir(parents=True, exist_ok=True)
                            fn.touch()

    def to_yaml(self, file: str) -> None:
        """Save the workflow to a yaml file."""
        yml_dict = {
            "name": self.name,
            "root": self.root.as_posix(),
            "config": self.config.to_dict(mode="json"),
            "wildcards": self.wildcards.to_dict(),
            "rules": [r.to_dict() for r in self.rules],
        }
        with open(file, "w") as f:
            yaml.dump(yml_dict, f, sort_keys=False)

    def run(
        self,
        max_workers=1,
    ) -> None:
        """Run the workflow.

        Parameters
        ----------
        max_workers : int, optional
            The maximum number of workers, by default 1.
            Only used when dryrun is False.
        missing_file_error : bool, optional
            Raise an error when a file is missing, by default False.
            This only works when dryrun is True.
        """
        nrules = len(self.rules)
        for i, rule in enumerate(self.rules):
            logger.info("Rule %d/%d: %s", i + 1, nrules, rule.rule_id)
            rule.run(max_workers=max_workers)

    def dryrun(self, missing_file_error: bool = False) -> None:
        """Dryrun the workflow.

        Parameters
        ----------
        missing_file_error : bool, optional
            Raise an error when a file is missing, by default False.
        """
        nrules = len(self.rules)
        input_files = []
        for i, rule in enumerate(self.rules):
            logger.info(f">> Rule {i+1}/{nrules}: {rule.rule_id}")
            output_files = rule.dryrun(
                missing_file_error=missing_file_error, input_files=input_files
            )
            input_files = list(set(input_files + output_files))

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
            for key, value in rule.method.output:
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
