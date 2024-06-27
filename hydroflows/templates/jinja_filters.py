import typing

from jinja2 import Environment

from hydroflows.methods.method import ExpandMethod

if typing.TYPE_CHECKING:
    from hydroflows.rule import Rule


def setup_rule_env(env: Environment, rule: "Rule"):

    def expand(val, key):
        """Expand the wildcards in a string."""
        # replace val with references to config or other rules
        kwargs = rule._kwargs
        if key in kwargs and kwargs[key].startswith("$"):
            if kwargs[key].startswith("$config"):
                # resolve to python dict-like access
                dict_keys = kwargs[key].split(".")[1:]
                v = 'config["' + '"]["'.join(dict_keys) + '"]'
            elif kwargs[key].startswith("$rules"):
                v = f"{kwargs[key][1:]}"
        else:
            expand_kwargs = []
            if isinstance(rule.method, ExpandMethod):
                for wc in rule.method.expand_values.keys():
                    if "{" + wc + "}" in str(val):
                        # NOTE wildcard values will be added by the workflow in upper case
                        expand_kwargs.append(f"{wc}={wc.upper()}")
            if expand_kwargs:
                for wc in rule.wildcards:
                    if "{" + wc + "}" in str(val):
                        # escape the wildcard in the value
                        val = str(val).replace("{" + wc + "}", "{{" + wc + "}}")
                # NOTE we assume product of all wildcards, this could be extended to also use zip
                expand_kwargs_str = ", ".join(expand_kwargs)
                v = f'expand("{val}", {expand_kwargs_str})'
            else:
                # no references or wildcards, just add the value with quotes
                v = f'"{val}"'
        return v

    env.filters["expand"] = expand
