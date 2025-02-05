"""Config adjust method."""

import re
from os.path import relpath
from pathlib import Path

from hydromt.config import configread, configwrite
from pydantic import ConfigDict, model_validator

from hydroflows.methods.wflow.wflow_utils import get_config, set_config
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`WflowConfig` method.
    """

    model_config = ConfigDict(extra="allow")

    wflow_toml: Path
    """The path to the wflow settings toml."""

    @model_validator(mode="after")
    def _optional_inputs(self):
        for key, value in self.to_dict().items():
            if key in self.__dict__:
                continue
            if not isinstance(value, Path):
                raise ValueError(f"{key} should be a pathlib.Path object.")
            self.__dict__[key] = value
        return self


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`WflowConfig` method.
    """

    wflow_out_toml: Path
    """The path to the resulting wflow settings toml."""


class Params(Parameters):
    """Parameters for the :py:class:`WflowConfig`.

    Instances of this class are used in the :py:class:`WflowConfig`
    method to define the required settings.
    """

    model_config = ConfigDict(extra="allow")

    output_dir: Path
    """Path to the outgoing directory."""

    config_basename: str = "wflow_sbm"
    """The basename (without the addition of wildcards) of the settings toml."""

    @model_validator(mode="after")
    def _typing_params(self):
        types = (Path, str, int, float, list, tuple)
        types_str = ", ".join([str(item) for item in types])
        for value in self.to_dict().values():
            if not isinstance(value, types):
                raise ValueError(
                    f"{type(value)} is not allowed, present either {types_str}"
                )


class WflowConfig(Method):
    """Wflow config adjustment method."""

    name: str = "wflow_config"

    _test_kwargs = {
        "wflow_toml": Path("wflow_sbm.toml"),
        "output_dir": Path("data"),
    }

    def __init__(self, wflow_toml: Path, output_dir: Path, **params):
        """Adjust and create a new settings file for wflow.

        Parameters
        ----------
        wflow_toml : Path
           Path to the (current) wflow settings toml.
        **params
            Additional parameters to pass to the WflowConfig instance.
            See :py:class:`wflow_config Params <hydroflows.methods.wflow.wflow_config.Params>`.

        See Also
        --------
        :py:class:`wflow_config Input <~hydroflows.methods.wflow.wflow_config.Input>`
        :py:class:`wflow_config Output <~hydroflows.methods.wflow.wflow_config.Output>`
        :py:class:`wflow_config Params <~hydroflows.methods.wflow.wflow_config.Params>`

        """
        # Filter pathing parameters from other params, as they are input
        input_kwargs = {}
        for key in list(params.keys()):
            if key.startswith("ri_"):
                input_kwargs[key] = Path(params.pop(key))
                continue

        self.params: Params = Params(output_dir=output_dir, **params)
        self.input: Input = Input(wflow_toml=wflow_toml, **input_kwargs)
        self.output: Output = Output(
            wflow_out_toml=self.params.output_dir
            / (self.params.config_basename + ".toml")
        )

    def run(self):
        """Run the wflow config method."""
        cfg = configread(self.input.wflow_toml)

        # Create local variables
        inputs = self.input.to_dict()
        params = self.params.to_dict()

        # Some other necessary variables
        old_parent = self.input.wflow_toml.parent
        new_parent = self.output.wflow_out_toml.parent
        reset = ["input.path_forcing", "input.path_static"]

        # Filter the inputs
        for key in inputs:
            m = re.findall("^ri_(\w+)$", key)
            if len(m) == 0:
                continue
            params[m[0]] = inputs[key]

        for key in self.params.__dict__:
            _ = params.pop(key)

        # Redirect paths to forcing and staticmaps
        for item in reset:
            value = get_config(cfg, item)
            full_path = Path(old_parent, value)
            new_path = Path(relpath(full_path, new_parent))
            set_config(cfg, item, new_path.as_posix())

        # Set the new entries by looping over the params
        for key, value in params.items():
            key = key.replace("__", ".")
            if isinstance(value, Path):
                value = Path(
                    relpath(value, new_parent),
                ).as_posix()
            set_config(cfg, key, value)

        # Write the new setting toml to drive
        configwrite(self.output.wflow_out_toml, cfg)
