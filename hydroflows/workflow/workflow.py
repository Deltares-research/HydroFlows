"""HydroFlows Workflow class.

This class is responsible for:
- main entry point for users to define workflows.
- storing and accessing rules, wildcards, and configuration.
- parsing workflows to a workflow engine.
- running workflows.
"""

import logging
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional, Union

import graphviz
import yaml
from jinja2 import Environment, PackageLoader

from hydroflows import __version__
from hydroflows.templates.jinja_snake_rule import JinjaSnakeRule
from hydroflows.workflow.method import ExpandMethod, Method, ReduceMethod
from hydroflows.workflow.reference import Ref
from hydroflows.workflow.rule import Rule
from hydroflows.workflow.rules import Rules
from hydroflows.workflow.wildcards import Wildcards
from hydroflows.workflow.workflow_config import WorkflowConfig

logger = logging.getLogger(__name__)


class Workflow:
    """Create a workflow instance.

    Parameters
    ----------
    config : Dict, optional
        The configuration of the workflow, by default None.
    wildcards : Dict, optional
        The wildcard keys and values of the workflow, by default None.
    """

    def __init__(
        self,
        name="hydroflows",
        config: Optional[Union[Dict, WorkflowConfig]] = None,
        wildcards: Optional[Dict] = None,
        root: Optional[Path] = None,
    ) -> None:
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

    def create_rule(self, method: Method, rule_id: Optional[str] = None) -> Rule:
        """Create a rule based on a method.

        Parameters
        ----------
        method : Method
            The method to create the rule from.
        rule_id : str, optional
            The rule id, by default None.
        """
        rule = Rule(method, self, rule_id)
        self.rules.set_rule(rule)
        return rule

    def create_rule_from_kwargs(
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
        m = Method.from_kwargs(str(method), **kwargs)
        self.create_rule(m, rule_id)

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
                raise ValueError(f"Rule {i + 1} invalid: not a dictionary.")
            if "method" not in rule.keys():
                raise ValueError(f"Rule {i + 1} invalid: 'method' name missing.")
            workflow.create_rule_from_kwargs(**rule)
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
            logger.info(f">> Rule {i + 1}/{nrules}: {rule.rule_id}")
            output_files = rule.dryrun(
                missing_file_error=missing_file_error, input_files=input_files
            )
            input_files = list(set(input_files + output_files))

    def plot_rulegraph(
        self, filename: str | Path | None = "rulegraph.svg", plot_rule_attrs=True
    ) -> graphviz.Digraph:
        """Plot the rulegraph.

        The rulegraph is a directed graph where the nodes are rules and the edges are dependencies.

        The nodes are colored based on the type of rule:
        Expand rules are colored blue, reduce rules are colored green,
        and rules with repeat wildcards are colored purple. Result rules are colored red.

        Parameters
        ----------
        filename : str, optional
            The filename of the rulegraph, by default "rulegraph.svg".
            The file is saved in the root directory of the workflow.
        plot_rule_attrs : bool, optional
            Plot the rule attributes (n runs and wildcards) in the node, by default True.

        Returns
        -------
        graphviz.Digraph
            The graphviz Digraph object.
        """
        node_attr = {
            "shape": "box",
            "style": "rounded",
            "fontname": "Courier",
            "fontsize": "12",
            "penwidth": "2",
        }
        edge_attr = {"penwidth": "2", "color": "grey"}
        graph = graphviz.Digraph(
            name=self.name, node_attr=node_attr, edge_attr=edge_attr
        )
        for rule in self.rules:
            # add the rule_id in bold
            name = f"""<b>{rule.rule_id}</b><BR/>"""
            # get rule attributes (n runs and ) from the rule object __repr__
            rule_attrs = ""
            if plot_rule_attrs:
                rule_attrs = "<BR/>".join(str(rule)[5:-1].split(",")[2:])
            # add node to graph with color based on rule type
            kwargs = {"color": "black"}
            if rule.rule_id in self.rules.result_rules:
                kwargs["color"] = "red"
            elif isinstance(rule.method, ExpandMethod):
                kwargs["color"] = "blue"
            elif isinstance(rule.method, ReduceMethod):
                kwargs["color"] = "green"
            elif len(rule.wildcards["repeat"]) > 0:
                kwargs["color"] = "purple"
            graph.node(rule.rule_id, f"<{name}{rule_attrs}>", **kwargs)
            # add edges (dependencies) to the graph
            for dep in self.rules.dependency_map[rule.rule_id]:
                graph.edge(dep, rule.rule_id)
        if filename is not None:
            graph.render(
                Path(filename).stem,
                directory=self.root,
                format=Path(filename).suffix[1:],
                cleanup=True,
            )
        return graph
