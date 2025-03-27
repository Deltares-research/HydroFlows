"""Workflow and components."""

from hydroflows.workflow.method import ExpandMethod, Method, ReduceMethod
from hydroflows.workflow.method_parameters import Parameters
from hydroflows.workflow.rule import Rule
from hydroflows.workflow.wildcards import Wildcards
from hydroflows.workflow.workflow import Workflow
from hydroflows.workflow.workflow_config import WorkflowConfig

__all__ = [
    "Method",
    "ExpandMethod",
    "ReduceMethod",
    "Parameters",
    "Rule",
    "Wildcards",
    "Workflow",
    "WorkflowConfig",
]
