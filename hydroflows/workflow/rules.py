"""HydroFlows Rules class.

This class is responsible for:
- storing and accessing rules in a workflow.
- mapping dependencies of rules.
- ordering rules based on dependencies.
"""

from itertools import chain
from typing import Iterator

from hydroflows.workflow.rule import Rule


class Rules:
    """Rules class.

    Rules are dynamically stored as attributes of the Rules class for easy access.
    The order of rules is stored in the names attribute.
    A dependency map is kept in the dependency_map attribute.
    """

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.names: list[str] = []
        """Ordered list of rule IDs."""

        self.dependency_map: dict[str, list[str]] = {}
        """Dictionary mapping rule IDs to their dependencies."""

        if rules:
            for rule in rules:
                self.set_rule(rule)

    def __repr__(self) -> str:
        """Return the representation of the rules."""
        rules_repr = "\n".join([str(self.get_rule(name)) for name in self.names])
        return f"[{rules_repr}]"

    def set_rule(self, rule: Rule) -> None:
        """Set rule."""
        rule_id = rule.rule_id
        self.__setitem__(rule_id, rule)

    def get_rule(self, rule_id: str) -> Rule:
        """Get rule based on rule_id."""
        return self.__getitem__(rule_id)

    @property
    def ordered_rules(self) -> list[Rule]:
        """Return a list of all rules."""
        return [self[rule_id] for rule_id in self.names]

    @property
    def result_rules(self) -> list[str]:
        """Return a list of all rules that are no a dependency of other rules."""
        all_dependencies = set(chain(*self.dependency_map.values()))
        all_rules = set(self.names)
        return sorted(all_rules - all_dependencies)

    def _detect_dependencies_rule(self, rule: Rule) -> list[str]:
        """Find all dependencies of rule_id by matching input values to output values of prev rules.

        This method updates dependency_map and returns list with rule_id of dependencies.
        """
        # Make list of inputs, convert to set of strings for quick matching
        inputs = rule.input
        inputs = list(chain(*inputs.values()))
        # order of inputs doesn't matter here so set() is fine
        inputs = set([str(item) for item in inputs])

        # Init dependency list
        dependency_list: list[str] = []
        for prev_rule in self.ordered_rules:
            # Make list of outputs as strings, outputs always paths anyways
            outputs = prev_rule.output
            outputs = list(chain(*outputs.values()))
            outputs = [str(item) for item in outputs]

            # Find if inputs, outputs share any element
            if not inputs.isdisjoint(outputs):
                dependency_list.append(prev_rule.rule_id)

        # Update dependency_map
        self.dependency_map[rule.rule_id] = dependency_list

        return dependency_list

    def _get_new_rule_index(self, rule: Rule) -> int:
        """Determine where the rule should be added in the ordered list of rules."""
        dependencies = self.dependency_map.get(rule.rule_id)
        if len(dependencies) > 0:
            ind = self.names.index(dependencies[-1]) + 1
            # If there is already a rule in that position, break tie based on loop_depth with highest loop depth last
            if ind != len(self.names) and rule._loop_depth > self[ind]._loop_depth:
                ind += 1
        # If rule input does not depend on others, put at beginning after other rules with no input dependencies.
        else:
            ind = len(
                [
                    rule_id
                    for rule_id in self.names
                    if len(self.dependency_map.get(rule_id)) == 0
                ]
            )
        return ind

    def _sort_repeat_wildcards(self, ind) -> None:
        if ind == 0:
            return
        prev_rule = self[ind - 1]
        rule = self[ind]
        wc_sort = prev_rule.wildcards["repeat"]
        wc_new = [name for name in rule.wildcards["repeat"] if name not in wc_sort]
        rule._wildcards["repeat"] = sorted(
            rule._wildcards["repeat"], key=lambda x: [*wc_sort, *wc_new].index(x)
        )

    # method for getting a rule using numerical index,
    # i.e. rules[0] and rules['rule_id'] are both valid
    def __getitem__(self, key: int | str) -> Rule:
        if isinstance(key, int) and key < len(self.names):
            key = self.names[key]
        if key not in self.names:
            raise ValueError(f"Rule {key} not found.")
        rule: Rule = getattr(self, key)
        return rule

    def __setitem__(self, key: str, rule: Rule) -> None:
        if not isinstance(rule, Rule):
            raise ValueError("Rule should be an instance of Rule.")
        if hasattr(self, key):
            if key in self.names:
                raise ValueError(f"Rule {key} already exists.")
            else:
                raise ValueError(f"Rule {key} is an invalid rule ID.")
        setattr(self, key, rule)
        # Detect dependencies and insert rule in correct position
        self._detect_dependencies_rule(rule)
        ind = self._get_new_rule_index(rule)
        self.names.insert(ind, key)
        self._sort_repeat_wildcards(ind)

    def __iter__(self) -> Iterator[Rule]:
        return iter([self[rule_id] for rule_id in self.names])

    def __next__(self) -> Rule:
        return next(self)

    def __len__(self) -> int:
        return len(self.names)
