"""Reference class to resolve cross references in the workflow."""

import inspect
from typing import TYPE_CHECKING, Any, Iterator, Optional

if TYPE_CHECKING:
    from hydroflows.workflow.method import Method
    from hydroflows.workflow.method_parameters import Parameters
    from hydroflows.workflow.workflow import Workflow
    from hydroflows.workflow.workflow_config import WorkflowConfig


__all__ = ["Ref"]


class Ref(object):
    """Cross reference class."""

    def __init__(
        self,
        ref: str,
        workflow: Optional["Workflow"] = None,
        value: Optional[Any] = None,
    ) -> None:
        """Create a cross reference instance.

        For example, the input of one rule can be the output of previous rule,
        or the input of one rule can be a value from the workflow config.

        Parameters
        ----------
        ref : str
            Reference to resolve provided as a dot-separated string.
            For config: `"$config.<key>"`, or `<config>.<key>`
            For wildcards: `"$wildcards.<key>"`
            For rules: `"$rules.<rule_name>.<component>.<key>"` or `"<method>.<component>.<key>"`
            Where <component> is one of "input", "output" or "params".
        workflow : Workflow, optional
            The workflow instance to which the reference belongs.
        value : Any, optional
            The value of the reference.
        """
        if workflow is not None:
            self._set_resolve_ref(ref, workflow)
        elif value is not None:
            self.ref = ref
            self.value = value
        else:
            raise ValueError("Either workflow or value should be provided.")

    @property
    def ref(self) -> str:
        """Reference string."""
        return self._ref

    @ref.setter
    def ref(self, ref: str) -> None:
        """Set reference."""
        if not isinstance(ref, str):
            raise ValueError("Reference should be a string.")
        ref_keys = ref.split(".")
        if ref_keys[0] == "$rules":
            if not len(ref_keys) >= 4 or ref_keys[2] not in [
                "input",
                "output",
                "params",
            ]:
                raise ValueError(
                    f"Invalid rule reference: {ref}. "
                    "A rule reference should be in the form rules.<rule_id>.<component>.<key>, "
                    "where <component> is one of input, output or params."
                )
        elif ref_keys[0] == "$config":
            if not len(ref_keys) >= 2:
                raise ValueError(
                    f"Invalid config reference: {ref}. "
                    "A config reference should be in the form config.<key>."
                )
        elif ref_keys[0] == "$wildcards":
            if not len(ref_keys) == 2:
                raise ValueError(
                    f"Invalid wildcard reference: {ref}. "
                    "A wildcard reference should be in the form wildcards.<key>."
                )
        else:
            raise ValueError(
                "Reference should start with '$rules', '$config', or '$wildcards'."
            )
        self._ref = ref

    @property
    def value(self) -> Any:
        """Reference value."""
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        """Set value."""
        if value is None:
            raise ValueError(
                f"Value should not be None. Reference {self.ref} possibly not resolved."
            )
        self._value = value

    def __repr__(self) -> str:
        return f"Ref({self.ref})"

    # try to mimic behavior as if Ref is value

    def __str__(self) -> str:
        # NOTE: this is required for Parameters
        return str(self.value)

    def __len__(self) -> int:
        return len(self.value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.value)

    def __next__(self) -> Any:
        return next(self.value)

    def __getitem__(self, *args) -> Any:
        return self.value.__getitem__(*args)

    # resolve ref

    def _set_resolve_ref(self, ref: str, workflow: "Workflow") -> None:
        """Set and resolve reference."""
        # import here to avoid circular imports
        from hydroflows.workflow.method import Method
        from hydroflows.workflow.workflow_config import WorkflowConfig

        ref_type = ref.split(".")[0]
        if ref_type == "$rules":
            self._set_resolve_rule_ref(ref, workflow)
        elif ref_type == "$config":
            self._set_resolve_config_ref(ref, workflow)
        elif ref_type == "$wildcards":
            self._set_resolve_wildcard_ref(ref, workflow)
        else:  # try to resolve as a global variable
            obj = _get_obj_from_caller_globals(ref_type, ref)
            if obj == workflow:
                ref = "$" + ".".join(ref.split(".")[1:])
                self._set_resolve_ref(ref, workflow)
            elif isinstance(obj, Method):
                self._resolve_method_obj_ref(ref, workflow, obj)
            elif isinstance(obj, WorkflowConfig):
                self._resolve_config_obj_ref(ref, workflow, obj)
            else:
                raise ValueError(f"Invalid reference: {ref}.")

    def _set_resolve_rule_ref(self, ref: str, workflow: "Workflow") -> None:
        """Resolve $rules reference."""
        self.ref = ref
        ref_keys = self.ref.split(".")
        rule_id, component, field = ref_keys[1:]
        method = workflow.rules.get_rule(rule_id).method
        parameters: "Parameters" = getattr(method, component)
        if field not in parameters.model_fields:
            raise ValueError(
                f"Invalid reference: {self.ref}. "
                f"Field {field} not found in rule {rule_id}.{component}."
            )
        self.value = getattr(parameters, ref_keys[3])

    def _set_resolve_config_ref(self, ref: str, workflow: "Workflow") -> Any:
        """Resolve $config reference."""
        self.ref = ref
        config = workflow.config.to_dict()
        self.value = _get_nested_value_from_dict(config, self.ref.split(".")[1:], ref)

    def _set_resolve_wildcard_ref(self, ref: str, workflow: "Workflow") -> Any:
        """Resolve $wildcards reference."""
        self.ref = ref
        wildcard = self.ref.split(".")[1]
        self.value = workflow.wildcards.get(wildcard)

    def _resolve_method_obj_ref(
        self, ref: str, workflow: "Workflow", method: "Method"
    ) -> Any:
        """Resolve reference to a Method object."""
        ref_keys = ref.split(".")
        if len(ref_keys) < 3:
            raise ValueError(
                f"Invalid method reference {ref}. "
                "A method reference should be in the form <method>.<component>.<field>"
            )
        rules = [rule for rule in workflow.rules if rule.method == method]
        if len(rules) == 0:
            raise ValueError(
                f"Invalid method reference {ref}. " "Method not added to the workflow"
            )
        rule_id = rules[0].rule_id
        component, field = ref_keys[-2], ref_keys[-1]
        ref = f"$rules.{rule_id}.{component}.{field}"
        self._set_resolve_rule_ref(ref, workflow)

    def _resolve_config_obj_ref(
        self, ref: str, workflow: "Workflow", config: "WorkflowConfig"
    ) -> Any:
        """Resolve reference to a WorkflowConfig object."""
        ref_keys = ref.split(".")
        if config != workflow.config:
            raise ValueError(
                f"Invalid config reference {ref}. " "Config not added to the workflow"
            )
        fields = ".".join(ref_keys[1:])
        ref = f"$config.{fields}"
        self._set_resolve_config_ref(ref, workflow)


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
