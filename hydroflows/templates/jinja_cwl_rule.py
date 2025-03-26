from copy import deepcopy
from itertools import product
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Union

from hydroflows._typing import filedirpath, outputdirpath
from hydroflows.utils.cwl_utils import map_cwl_types, wildcard_inputs_nested
from hydroflows.utils.parsers import get_wildcards

if TYPE_CHECKING:
    from hydroflows.workflow.rule import Rule


class JinjaCWLRule:
    """Class for exporting to CWL"""

    def __init__(self, rule: "Rule"):
        self.rule = rule
        self.id = rule.rule_id
        self.method_name = rule.method.name
        self.loop_depth = rule._loop_depth

        self._input: Dict[str, Dict] = {}
        self._input_wildcards: list[str] = []
        self._output: Dict[str, Dict] = {}

        self._add_input_to_config()
        self._add_method_params_to_config()
        self._set_input()
        self._set_input_wildcards()
        self._set_output()

    @property
    def input(self) -> Dict[str, Dict]:
        """Return nested dict of input keys and CWL info."""
        return self._input

    @property
    def output(self) -> Dict[str, Dict]:
        """Return nested dict of output keys and CWL info."""
        return self._output

    @property
    def input_wildcards(self) -> List[str]:
        """Return list of repeat wildcards occuring in inputs."""
        return self._input_wildcards

    def _set_input(self) -> Dict[str, str]:
        """Get input dict for CWL step."""
        refs = self.rule.method.input.to_dict(filter_types=Path, return_refs=True)
        inputs = {}
        # Reduce wildcards determines type File[] vs type File
        reduce_wc = None
        if self.rule.wildcards["reduce"]:
            (reduce_wc,) = self.rule.wildcards["reduce"]

        for key, val in refs.items():
            if isinstance(val, Path):
                val = val.as_posix()
            ref = self.rule.workflow.get_ref(val)
            inputs[key] = map_cwl_types(ref.value)
            # Set the source of the input (from prev rule, config)
            if "$config" in ref.ref:
                inputs[key]["source"] = val.split(".")[-1]
            if "$rules" in ref.ref:
                tmp = val.split(".")
                inputs[key]["source"] = f"{tmp[-3]}/{tmp[-1]}"
            # Set input type
            if reduce_wc and key in self.rule.wildcard_fields[reduce_wc]:
                inputs[key]["type"] += "[]"
                inputs[key]["separator"] = '", "'
            if isinstance(ref.value, filedirpath):
                inputs[key + "_dir"] = {
                    "type": "Directory",
                    "source": inputs[key]["source"] + "_dir",
                    "value": {"class": "Directory", "path": ref.value.parent},
                    "folderpath": True,
                }
                # This is to ensure the proxy file and the dir it represents have the correct parentage
                inputs[key]["valueFrom"] = f"$(inputs.{key}_dir.path)/$(self.basename)"
            # ref to config does not maintain folderpath typing (reverts it instead to Path)
            elif isinstance(getattr(self.rule.method.input, key), filedirpath):
                inputs[key + "_dir"] = {
                    "type": "Directory",
                    "source": inputs[key]["source"] + "_dir",
                    "value": {"class": "Directory", "path": ref.value.parent},
                    "folderpath": True,
                }
                inputs[key]["valueFrom"] = f"$(inputs.{key}_dir.path)/$(self.basename)"
                # Add new folder input to config
                config_key = f"{key}_dir"
                # config_ref = "$config." + config_key
                self.rule.workflow.config = self.rule.workflow.config.model_copy(
                    update={config_key: ref.value.parent}
                )

        # Add params to inputs
        params = self.rule.method.params.to_dict(return_refs=True)
        for key, val in params.items():
            default_value = self.rule.method.params.model_fields.get(key).default
            if val == default_value:
                continue
            # Set source for input to correct reference
            if isinstance(val, str) and "$" in val:
                inputs[key] = map_cwl_types(self.rule.method.params.to_dict()[key])
                inputs[key]["source"] = val.split(".")[-1]
                # wildcards have _wc added when turned into workflow inputs
                if "wildcards" in val:
                    inputs[key]["source"] += "_wc"
            else:
                inputs[key] = map_cwl_types(val)
            inputs[key]["type"] += "?"

        self._input = inputs

    def _set_input_wildcards(self) -> str:
        """Get wildcards that need to be included in CWL step input."""
        if self.rule.wildcards["repeat"]:
            wc = self.rule.wildcards["repeat"]
            wc = [item + "_wc" for item in wc]
            self._input_wildcards = wc

    def _set_output(self) -> Dict[str, str]:
        """Get outputs of CWL step."""
        results = self.rule.method.output.to_dict(mode="python", filter_types=Path)
        out_root = ""
        outputs = {}
        wc_expand = self.rule.wildcards["expand"]
        for key, val in results.items():
            if not any(
                [isinstance(par[1], outputdirpath) for par in self.rule.method.params]
            ):
                for _, in_value in self.rule.method.input.to_dict().items():
                    if val.is_relative_to(in_value.parent):
                        out_root = in_value.parents[1]

            if out_root:
                out_value = val.relative_to(out_root).as_posix()
            else:
                out_value = val.as_posix()
            out_eval = val.as_posix()
            out_type = "File"
            if self.input_wildcards:
                # This is for repeat (n-to-n) methods.
                # We dont want every possible output value here
                # only replace {wildcard} by CWL-style $(input.wildcard)
                for wc in self.input_wildcards:
                    wc = wc.replace("_wc", "")
                    out_value = out_value.replace(
                        ("{" + f"{wc}" + "}"), f"$(inputs.{wc}_wc)"
                    )
                    out_eval = out_eval.replace(
                        ("{" + f"{wc}" + "}"), f"$(inputs.{wc}_wc)"
                    )
            if wc_expand and any(get_wildcards(val, wc_expand)):
                # This is for expand (1-to-n) methods
                # Here we want every possible value for the expand wildcards
                wc_dict = self.rule.method.expand_wildcards
                wc_values = list(product(*wc_dict.values()))
                out_value = [
                    out_value.format(**dict(zip(wc_expand, wc))) for wc in wc_values
                ]
                out_eval = [
                    out_eval.format(**dict(zip(wc_expand, wc))) for wc in wc_values
                ]
                out_type += "[]"
            if not isinstance(out_value, list):
                out_value = [out_value]
            if not isinstance(out_eval, list):
                out_eval = [out_eval]
            outputs[key] = {
                "type": out_type,
                "value": out_value,
                "eval": out_eval,
            }
            if isinstance(val, filedirpath):
                outputs[key + "_dir"] = {
                    "type": out_type.replace("File", "Directory"),
                    "value": [Path(out).parent.as_posix() for out in out_value],
                    "eval": [Path(out).parent.as_posix() for out in out_eval],
                }
                if "[]" in out_type and len(set(outputs[key + "_dir"]["value"])) == 1:
                    outputs[key + "_dir"]["value"] = list(
                        set(outputs[key + "_dir"]["value"])
                    )
                    outputs[key + "_dir"]["eval"] = list(
                        set(outputs[key + "_dir"]["eval"])
                    )
                    outputs[key + "_dir"]["type"] = outputs[key + "_dir"][
                        "type"
                    ].replace("[]", "")

        self._output = outputs

    def _add_input_to_config(self) -> None:
        ref_updates = {}
        conf_updates = {}

        # unpack existing config
        conf_keys = self.rule.workflow.config.keys
        conf_values = self.rule.workflow.config.values

        for key, value in self.rule.method.input:
            if key in self.rule.method.input._refs or value is None:
                continue
            if isinstance(value, Path):
                value = value.as_posix()
            # Check if value already exists in config, if so make ref to config
            if value in conf_values:
                conf_key = conf_keys[conf_values.index(value)]
                ref_updates.update({key: "$config." + conf_key})
            else:
                conf_key = f"{self.id}_{key}"
                conf_ref = "$config." + conf_key
                # input to config
                conf_updates.update({conf_key: value})
                # update refs
                ref_updates.update({key: conf_ref})

        self.rule.method.input._refs.update(ref_updates)
        self.rule.workflow.config = self.rule.workflow.config.model_copy(
            update=conf_updates
        )

    def _add_method_params_to_config(self) -> None:
        """Add method params to the config and update the method params refs."""
        ref_updates = {}
        conf_updates = {}

        for p in self.rule.method.params:
            key, value = p
            # Check if key can be found in method Params class
            if key in self.rule.method.params.model_fields:
                default_value = self.rule.method.params.model_fields.get(key).default
            else:
                default_value = None

            # Skip if key is already a ref
            if key in self.rule.method.params._refs:
                continue

            elif value != default_value:
                config_key = f"{self.id}_{key}"
                conf_updates.update({config_key: value})

                config_ref = "$config." + config_key
                ref_updates.update({key: config_ref})

        self.rule.method.params._refs.update(ref_updates)
        self.rule.workflow.config = self.rule.workflow.config.model_copy(
            update=conf_updates
        )


class JinjaCWLWorkflow:
    """Class for exporting workflow to CWL."""

    def __init__(
        self, rules: List[JinjaCWLRule], dryrun: bool = False, start_loop_depth: int = 0
    ):
        self.rules = rules
        self.workflow = self.rules[0].rule.workflow
        self.config = self.workflow.config
        self.start_loop = start_loop_depth
        self.dryrun = dryrun
        self.id = f"subworkflow_{self.rules[0].id}"

        self._steps: List[Union[JinjaCWLRule, "JinjaCWLWorkflow"]] = []
        self._input: Dict[str, Dict] = {}
        self._output: Dict[str, Dict] = {}
        self._input_scatter: List[str] = []
        self._workflow_input = {}

        self._set_steps()
        self._set_output()
        self._set_input()
        # input scatter only needed for subworkflows
        if self.start_loop > 0:
            self._set_input_scatter()
        self._set_workflow_input()

    @property
    def steps(self) -> List[Union[JinjaCWLRule, "JinjaCWLWorkflow"]]:
        """Return list of steps and subworkflows."""
        return self._steps

    @property
    def input(self) -> Dict[str, Dict]:
        """Return nested dict of input keys and info."""
        return self._input

    @property
    def output(self) -> Dict[str, Dict]:
        """Return nest dict of output keys and info."""
        return self._output

    @property
    def input_scatter(self) -> List[str]:
        """Return list of inputs that are scattered over in CWL workflow."""
        return self._input_scatter

    @property
    def workflow_input(self) -> Dict[str, str]:
        """Return dict of items to be parsed to config file."""
        return self._workflow_input

    def _set_steps(self):
        """Set list of steps and subworkflows."""
        step_list = deepcopy(self.rules)

        sub_wf = [rule for rule in step_list if rule.loop_depth > self.start_loop]
        indices = [i for i, x in enumerate(step_list) if x in sub_wf]

        if sub_wf:
            step_list[indices[0] : indices[-1] + 1] = [
                JinjaCWLWorkflow(rules=sub_wf, start_loop_depth=self.start_loop + 1)
            ]

        self._steps = step_list

    def _set_input(self):
        """Set CWL workflow inputs to be workflog.config + wildcards."""
        input_dict = {}
        conf_keys = self.workflow.config.keys
        conf_values = self.workflow.config.values
        ids = [rule.id for rule in self.rules]
        step_ids = [step.id for step in self.steps]

        # copy inputs from steps
        for step in self.steps:
            if isinstance(step, JinjaCWLRule):
                ins = deepcopy(step.input)
                for key, info in ins.items():
                    # Set correct format for input source
                    if "source" in info and "/" not in info["source"]:
                        if info["source"] in conf_keys:
                            in_val = conf_values[conf_keys.index(info["source"])]
                        elif info["source"] in self.workflow.wildcards.names:
                            in_val = self.workflow.wildcards.get(info["source"])
                        else:
                            in_val = info["value"]
                        if len(get_wildcards(in_val)) > 1:
                            wc = get_wildcards(in_val)
                            wc_sort = [
                                name
                                for name in self.workflow.wildcards.names
                                if name in wc
                            ]
                            in_val_eval = wildcard_inputs_nested(
                                in_val, self.workflow, wc_sort
                            )
                            input_dict[info["source"]] = map_cwl_types(in_val_eval)
                            input_dict[info["source"]]["value"] = str(in_val)
                        else:
                            input_dict[info["source"]] = map_cwl_types(in_val)
                    elif "source" in info:
                        if key in input_dict:
                            input_dict[key + f"_{step.id}"] = info
                        else:
                            input_dict[key] = info
                        if not any([id in info["source"] for id in step_ids]):
                            # handle inputs being reduced over
                            if step.rule.wildcards["reduce"]:
                                # original source of input
                                rule_id = [id for id in ids if id in info["source"]][0]
                                # find subworkflow original source is in
                                sub_wfs = [
                                    wf
                                    for wf in self.steps
                                    if isinstance(wf, JinjaCWLWorkflow)
                                ]
                                for sub_wf in sub_wfs:
                                    new_ids = [sub_step.id for sub_step in sub_wf.steps]
                                    if any([new_id in rule_id for new_id in new_ids]):
                                        final_id = sub_wf.id
                                source = info["source"].replace(rule_id, final_id)
                                step._input[key]["source"] = source

                            else:
                                step._input[key]["source"] = key
            # Copy inputs from subworkflow
            elif isinstance(step, JinjaCWLWorkflow):
                ins = deepcopy(step.input)
                for key in ins:
                    if key in list(self.output.keys()):
                        ins[key]["source"] = self.output[key]["outputSource"]
                    if key in step.input_scatter and "_wc" not in key:
                        ins[key]["type"] += "[]"
                input_dict.update(ins)

        # Delete any inputs with sources to other steps
        tmp = deepcopy(input_dict)
        for key, info in tmp.items():
            if "source" in info:
                if (
                    any([id in info["source"] for id in ids])
                    and "_wc" not in info["source"]
                ):
                    input_dict.pop(key)

        # Add wildcards to input
        for wc in self.rules[0].input_wildcards:
            input_dict.update({wc: {"type": "string[]", "source": wc}})

        self._input = input_dict

    def _set_output(self):
        """Set CWL workflow outputs to be outputs of all rules."""
        output_dict = {}

        # copy outputs from cwl rule
        for step in self.steps:
            for id, info in step.output.items():
                output_dict[id] = {
                    "type": info["type"],
                    "outputSource": f"{step.id}/{id}",
                    "value": info["value"],
                }
                # Make sure outputs produced by subworkflows are labeled as array outputs
                # This can give output types with [][], corrected for in jinja template
                if "subworkflow" in output_dict[id]["outputSource"]:
                    output_dict[id]["type"] += "[]"
        self._output = output_dict

    def _set_input_scatter(self) -> List[str]:
        """Set inputs which need to be scattered over."""
        wc = self.rules[0].rule.wildcards["repeat"]
        ins = self.input
        scatters = []

        # Fetch all inputs with relevant wildcard
        for key, info in ins.items():
            if info["type"] == "File" or info["type"] == "Directory":
                val = info["value"]["path"]
            elif "value" in info:
                val = info["value"]
            else:
                continue
            if any(get_wildcards(val, wc)):
                scatters.append(key)
                if "[]" in info["type"]:
                    num_brackets = len(get_wildcards(val)) - len(get_wildcards(val, wc))
                    self._input[key]["type"] = (
                        self._input[key]["type"].split("[", 1)[0] + "[]" * num_brackets
                    )

        for item in wc:
            scatters.append(item + "_wc")

        # Make sure the correct wildcards are treated as single input vs array input
        for key, info in ins.items():
            if "_wc" in key:
                # wildcards that are scattered over should be single input
                if key in scatters and "[]" in info["type"]:
                    self._input[key]["type"] = self._input[key]["type"].replace(
                        "[]", "", 1
                    )
                # Wildcards that are only scattered over in a subworkflow should be array inputs
                if key not in scatters and "[]" not in info["type"]:
                    self._input[key]["type"] += "[]"
        # Correct input_scatter of subworkflow
        for step in self.steps:
            if isinstance(step, JinjaCWLWorkflow):
                scatter_keys = [key for key in step.input_scatter if "_wc" not in key]
                scatter_vals = [step.input[key]["value"] for key in scatter_keys]
                scatter_vals = [
                    val["path"] if isinstance(val, Dict) else val
                    for val in scatter_vals
                ]
                for item in wc:
                    if (item + "_wc") in step.input_scatter:
                        step.input_scatter.pop(step.input_scatter.index(item + "_wc"))
                rem_wc = [wc for wc in step.input_scatter if "_wc" in wc]
                rem_wc = [wc.replace("_wc", "") for wc in rem_wc]
                for key in scatter_keys:
                    val = scatter_vals[scatter_keys.index(key)]
                    if not any(get_wildcards(val, rem_wc)):
                        step.input_scatter.pop(step.input_scatter.index(key))
                    # if key in scatters:
                    #     scatters.pop(scatters.index(key))
        self._input_scatter = scatters

    def _set_workflow_input(self):
        input_dict = {}
        for key, value in self.config:
            tmp = value
            if isinstance(tmp, Path):
                tmp = value.as_posix()
            if isinstance(tmp, str) and "{" in tmp:
                wildcards = get_wildcards(tmp)
                if len(wildcards) > 1:
                    wildcards_sorted = [
                        name
                        for name in self.workflow.wildcards.names
                        if name in wildcards
                    ]
                    new_val = wildcard_inputs_nested(
                        tmp, self.workflow, wildcards_sorted
                    )
                else:
                    wc_values = [self.workflow.wildcards.get(wc) for wc in wildcards]
                    wc_tuples = list(product(*wc_values))
                    new_val = [
                        tmp.format(**dict(zip(wildcards, tup))) for tup in wc_tuples
                    ]
                    if isinstance(value, Path) or Path(value).suffix:
                        new_val = [Path(val) for val in new_val]
            else:
                new_val = value

            input_dict[key] = map_cwl_types(new_val)
        for wc in self.workflow.wildcards.names:
            input_dict[wc + "_wc"] = {
                "type": "string[]",
                "value": self.workflow.wildcards.get(wc),
            }

        if self.dryrun:
            input_dict["dryrun"] = {"type": "boolean", "value": True}
            input_dict["touch_output"] = {"type": "boolean", "value": True}

        self._workflow_input = input_dict
