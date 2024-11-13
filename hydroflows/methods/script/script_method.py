"""Method to run scripts."""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Union

from pydantic import ConfigDict, ValidationError, model_validator

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


class ScriptParams(Parameters):
    """Parameters for ScriptMethod class."""

    # Allow extra fields in the model
    model_config = ConfigDict(extra="allow")

    script: Path
    """Path to the script file."""

    @model_validator(mode="before")
    @classmethod
    def _json_to_dict(cls, data: Any) -> Any:
        # check if json and convert to dict
        if isinstance(data, dict):
            for key, value in data.items():
                if (
                    isinstance(value, str)
                    and value.startswith("{")
                    and value.endswith("}")
                ):
                    # replace single quotes with double quotes
                    try:
                        data[key] = json.loads(value.replace("'", '"'))
                    except Exception:
                        pass
        return data


class ScriptInputOutput(Parameters):
    """Input/Output parameters for ScriptMethod class."""

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def _input_to_dict(cls, data: Any) -> Any:
        """Convert the input field to a dictionary."""
        # check if json and convert to dict
        if isinstance(data, str) and data.startswith("{") and data.endswith("}"):
            # replace single quotes with double quotes
            data = json.loads(data.replace("'", '"'))
        # check if single path and convert to dict
        elif isinstance(data, (Path, str)):
            data = {"input1": data}
        # check if list and convert to dict
        elif isinstance(data, list):
            data = {f"input{i+1}": item for i, item in enumerate(data)}
        return data

    @model_validator(mode="after")
    def check_extra_fields_are_paths(self):
        """Check that all extra fields are Path types."""
        for key, value in self:
            try:
                setattr(self, key, Path(value))
            except Exception:
                raise ValidationError(f"{key} not a Path ({value})")
        return self


class ScriptMethod(Method):
    """Script method class."""

    name = "script_method"

    _test_kwargs = {
        "script": Path("script.py"),
        "input": [Path("input.txt"), Path("input2.txt")],
        "output": Path("output.txt"),
        "param1": "value1",
        "param2": {"a": 1, "b": 2},
    }

    def __init__(
        self,
        script: Path,
        input: Union[Path, List[Path], Dict[str, Path]],
        output: Union[Path, List[Path], Dict[str, Path]],
        **params,
    ) -> None:
        """Initialize the class.

        Parameters
        ----------
        script : Path
            Path to the script file.
        input : Union[Path, List[Path], Dict[str, Path]]
            Input files.
        output : Union[Path, List[Path], Dict[str, Path]]
            Output files.
        params : Dict
            Parameters.
        """
        self.input: ScriptInputOutput = ScriptInputOutput.model_validate(input)
        self.output: ScriptInputOutput = ScriptInputOutput.model_validate(output)
        self.params: ScriptParams = ScriptParams(script=script, **params)

    def run(self):
        """Run the python script."""
        # add input, params and output as json argument
        cmd = ["python", self.params.script.as_posix(), self.json_kwargs]
        # run with subprocess
        subprocess.run(cmd, check=True)

    @property
    def json_kwargs(self):
        """Return input, params and output as json string."""
        return json.dumps(self.to_dict(posix_path=True))

    def to_kwargs(
        self,
        mode="json",
        exclude_defaults=True,
        posix_path=False,
        return_refs=False,
        **kwargs,
    ):
        """Convert the method to a dictionary of keyword arguments."""
        kwargs = dict(
            mode=mode,
            exclude_defaults=exclude_defaults,
            posix_path=posix_path,
            return_refs=return_refs,
            **kwargs,
        )
        return {
            "input": self.input.to_dict(**kwargs),
            "output": self.output.to_dict(**kwargs),
            **self.params.to_dict(**kwargs),
        }
