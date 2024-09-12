"""Reference class to resolve cross references in the workflow."""

import inspect
import weakref
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
        workflow: "Workflow",
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
        """
        self.workflow = workflow  # set weakref to workflow
        self._set_resolve_ref(ref)

    @property
    def workflow(self) -> "Workflow":
        """Get the workflow instance."""
        return self._workflow_ref()

    @workflow.setter
    def workflow(self, workflow: "Workflow") -> None:
        """Set the workflow instance."""
        self._workflow_ref = weakref.ref(workflow)

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
            components = ["input", "output", "params"]
            if not len(ref_keys) >= 4 or ref_keys[2] not in components:
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

    @property
    def is_expand_field(self) -> bool:
        """Check if the reference is to an expand field."""
        if not self.ref.startswith("$rules"):
            return False
        rule_id, component, field = self.ref.split(".")[1:]
        if component != "output":
            return False
        rule = self.workflow.rules.get_rule(rule_id)
        expand_wildcard = rule.wildcards.get("expand", [])
        expand_fields = []
        for wc in expand_wildcard:
            expand_fields.extend(rule.wildcard_fields[wc])
        if field in expand_fields:
            return True
        return False

    def get_str_value(self, posix_path=True, quote_str=True, **kwargs) -> str:
        """Get string value."""
        if not self.ref.startswith("$rules"):
            return str(self.value)
        rule_id, component, field = self.ref.split(".")[1:]
        rule = self.workflow.rules.get_rule(rule_id).method
        comp: "Parameters" = getattr(rule, component)
        val = comp.to_dict(
            mode="json",
            posix_path=posix_path,
            quote_str=quote_str,
            include=[field],
            **kwargs,
        )[field]
        return str(val)

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

    def _set_resolve_ref(self, ref: str) -> None:
        """Set and resolve reference."""
        # import here to avoid circular imports
        from hydroflows.workflow.method import Method
        from hydroflows.workflow.workflow_config import WorkflowConfig

        ref_type = ref.split(".")[0]
        if ref_type == "$rules":
            self._set_resolve_rule_ref(ref)
        elif ref_type == "$config":
            self._set_resolve_config_ref(ref)
        elif ref_type == "$wildcards":
            self._set_resolve_wildcard_ref(ref)
        else:  # try to resolve as a global variable
            obj = _get_obj_from_caller_globals(ref_type, ref)
            if obj == self.workflow:
                ref = "$" + ".".join(ref.split(".")[1:])
                self._set_resolve_ref(ref)
            elif isinstance(obj, Method):
                self._resolve_method_obj_ref(ref, obj)
            elif isinstance(obj, WorkflowConfig):
                self._resolve_config_obj_ref(ref, obj)
            else:
                raise ValueError(f"Invalid reference: {ref}.")

    def _set_resolve_rule_ref(self, ref: str) -> None:
        """Resolve $rules reference."""
        self.ref = ref
        ref_keys = self.ref.split(".")
        rule_id, component, field = ref_keys[1:]
        method = self.workflow.rules.get_rule(rule_id).method
        parameters: "Parameters" = getattr(method, component)
        if field not in parameters.model_fields:
            raise ValueError(
                f"Invalid reference: {self.ref}. "
                f"Field {field} not found in rule {rule_id}.{component}."
            )
        self.value = getattr(parameters, ref_keys[3])

    def _set_resolve_config_ref(self, ref: str) -> Any:
        """Resolve $config reference."""
        self.ref = ref
        config = self.workflow.config.to_dict()
        self.value = _get_nested_value_from_dict(config, self.ref.split(".")[1:], ref)

    def _set_resolve_wildcard_ref(self, ref: str) -> Any:
        """Resolve $wildcards reference."""
        self.ref = ref
        wildcard = self.ref.split(".")[1]
        self.value = self.workflow.wildcards.get(wildcard)

    def _resolve_method_obj_ref(self, ref: str, method: "Method") -> Any:
        """Resolve reference to a Method object."""
        ref_keys = ref.split(".")
        if len(ref_keys) < 3:
            raise ValueError(
                f"Invalid method reference {ref}. "
                "A method reference should be in the form <method>.<component>.<field>"
            )
        rules = [rule for rule in self.workflow.rules if rule.method == method]
        if len(rules) == 0:
            raise ValueError(
                f"Invalid method reference {ref}. " "Method not added to the workflow"
            )
        rule_id = rules[0].rule_id
        component, field = ref_keys[-2], ref_keys[-1]
        ref = f"$rules.{rule_id}.{component}.{field}"
        self._set_resolve_rule_ref(ref)

    def _resolve_config_obj_ref(self, ref: str, config: "WorkflowConfig") -> Any:
        """Resolve reference to a WorkflowConfig object."""
        ref_keys = ref.split(".")
        if config != self.workflow.config:
            raise ValueError(
                f"Invalid config reference {ref}. " "Config not added to the workflow"
            )
        fields = ".".join(ref_keys[1:])
        ref = f"$config.{fields}"
        self._set_resolve_config_ref(ref)


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
