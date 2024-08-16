"""Reference class to resolve cross references in the workflow."""

import inspect
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from hydroflows.workflow.method import Method
    from hydroflows.workflow.method_parameters import Parameters
    from hydroflows.workflow.workflow import Workflow
    from hydroflows.workflow.workflow_config import WorkflowConfig


class Ref(object):
    """Cross reference class."""

    def __init__(
        self,
        ref: str,
        workflow: "Workflow",
    ) -> None:
        """Create a cross reference instance.

        For example, the input of one rule can be the output of previous rule,
        or the input of one rule can be a value from the workflow config.

        Parameters
        ----------
        ref : str
            Reference to resolve provided as a dot-separated string.
            For rules: `"$rules.<rule_name>.<component>.<key>"`
            For methods: `"<method>.<component>.<key>"`
            For config: `"$config.<key>"`, or `<config>.<key>`
            Where <component> is one of "input", "output" or "params".
        workflow : Workflow
            The workflow instance to which the reference belongs.
        """
        if not isinstance(ref, str):
            raise ValueError("Reference should be a string.")
        self.ref: str = ref
        """Reference string."""

        self.value: Any = None
        """Reference value."""

        self._resolve_ref(workflow)

    def __repr__(self) -> str:
        return f"Ref({self.ref})"

    def __str__(self) -> str:
        # NOTE: this is required for Parameters
        return str(self.value)

    def _resolve_ref(self, workflow: "Workflow") -> None:
        # import here to avoid circular imports
        from hydroflows.workflow.method import Method
        from hydroflows.workflow.workflow_config import WorkflowConfig

        ref_type = self.ref.split(".")[0]
        if ref_type == "$rules":
            self._resolve_rule_ref(workflow)
        elif ref_type == "$config":
            self._resolve_config_ref(workflow)
        else:  # try to resolve as a global variable
            obj = _get_obj_from_caller_globals(ref_type, self.ref)
            if obj == workflow:
                self.ref = "$" + ".".join(self.ref.split(".")[1:])
                self._resolve_ref(workflow)
            elif isinstance(obj, Method):
                self._resolve_method_obj_ref(workflow, obj)
            elif isinstance(obj, WorkflowConfig):
                self._resolve_config_obj_ref(workflow, obj)
            else:
                raise ValueError(f"Invalid reference: {self.ref}.")

    def _resolve_rule_ref(self, workflow: "Workflow") -> None:
        """Resolve reference another rule."""
        ref_keys = self.ref.split(".")
        if not len(ref_keys) >= 4 or ref_keys[2] not in ["input", "output", "params"]:
            raise ValueError(
                f"Invalid rule reference: {self.ref}. "
                "A rule reference should be in the form rules.<rule_id>.<component>.<key>, "
                "where <component> is one of input, output or params."
            )
        rule_id, component, field = ref_keys[1:]
        method = workflow.rules.get_rule(rule_id).method
        parameters: "Parameters" = getattr(method, component)
        if field not in parameters.model_fields:
            raise ValueError(
                f"Invalid reference: {self.ref}. "
                f"Field {field} not found in rule {rule_id}.{component}."
            )
        self.value = getattr(parameters, ref_keys[3])

    def _resolve_config_ref(self, workflow: "Workflow") -> Any:
        """Resolve reference to config."""
        config = workflow.config.to_dict()
        self.value = _get_nested_value_from_dict(
            config, self.ref.split(".")[1:], self.ref
        )

    def _resolve_method_obj_ref(self, workflow: "Workflow", method: "Method") -> Any:
        """Resolve reference to global variables."""
        ref_keys = self.ref.split(".")
        if len(ref_keys) < 3:
            raise ValueError(
                f"Invalid method reference {self.ref}. "
                "A method reference should be in the form <method>.<component>.<field>"
            )
        rules = [rule for rule in workflow.rules if rule.method == method]
        if len(rules) == 0:
            raise ValueError(
                f"Invalid method reference {self.ref}. "
                "Method not added to the workflow"
            )
        rule_id = rules[0].rule_id
        component, field = ref_keys[-2], ref_keys[-1]
        self.ref = f"$rules.{rule_id}.{component}.{field}"
        self._resolve_rule_ref(workflow)

    def _resolve_config_obj_ref(
        self, workflow: "Workflow", config: "WorkflowConfig"
    ) -> Any:
        """Resolve reference to workflow config."""
        ref_keys = self.ref.split(".")
        if len(ref_keys) < 2:
            raise ValueError(
                f"Invalid config reference {self.ref}. "
                "A config reference should be in the form <config>.<field>"
            )
        if config != workflow.config:
            raise ValueError(
                f"Invalid config reference {self.ref}. "
                "Config not added to the workflow"
            )
        fields = ".".join(ref_keys[1:])
        self.ref = f"$config.{fields}"
        self._resolve_config_ref(workflow)


def _get_nested_value_from_dict(
    d: dict, keys: list, full_reference: Optional[str] = None
) -> Any:
    """Get nested value from dictionary."""
    if full_reference is None:
        full_reference = ".".join(keys)
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            raise KeyError(f"Key not found: {full_reference}")
    return d


def _get_obj_from_caller_globals(var_name: str, ref: str) -> Any:
    """Get global variable."""
    cf = inspect.currentframe()
    while True:
        code_context = inspect.getframeinfo(cf).code_context
        if code_context and ref in str(code_context):
            break
        cf = cf.f_back
    return cf.f_globals.get(var_name, None)
