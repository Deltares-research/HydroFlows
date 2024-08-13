"""Reference class to resolve cross references in the workflow."""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from hydroflows.workflow import Workflow


class Ref(object):
    """Cross reference class."""

    def __init__(self, ref: str, workflow: "Workflow") -> None:
        """Create a cross reference instance.

        For example, the input of one rule can be the output of previous rule,
        or the input of one rule can be a value from the workflow config.

        Parameters
        ----------
        ref : str
            Reference to resolve provided as a dot-separated string.
            For rules: rules.<rule_name>.<rule_component>.<key>,
            where <rule_component> is one of input, output or params.
            For config: config.<key>.
        workflow : Workflow
            The workflow instance to which the reference belongs.
        """
        self.ref: str = ref
        self.value: Any = None

        ref_type = self.ref.split(".")[0]

        match ref_type:
            case "rules":
                self.value = self._resolve_rule_ref(workflow)
            case "config":
                self.value = self._resolve_config_ref(workflow)
            case _:
                raise ValueError(
                    f"Invalid reference: {self.ref}. References should start with config or rules."
                )

    def _resolve_rule_ref(self, workflow: "Workflow") -> Any:
        """Resolve reference another rule."""
        ref_keys = self.ref.split(".")

        if not len(ref_keys) >= 4:
            raise ValueError(
                f"Invalid rule reference: {self.ref}. "
                "A rule reference should be in the form rules.<rule_name>.<rule_component>.<key>, "
                "where <rule_component> is one of input, output or params."
            )
        rule_dict = workflow.get_rule(ref_keys[1]).to_dict()
        value = _get_nested_value_from_dict(rule_dict, ref_keys[2:], self.ref)
        return value

    def _resolve_config_ref(self, workflow: "Workflow") -> Any:
        """Resolve reference to config."""
        value = _get_nested_value_from_dict(
            workflow.config, self.ref.split(".")[1:], self.ref
        )
        return value


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
