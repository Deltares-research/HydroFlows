"""Prepare FloodAdapt database builder."""

import os
import shutil
from pathlib import Path

import toml
from hydromt.config import configread

from hydroflows.config import HYDROMT_CONFIG_DIR
from hydroflows.methods.flood_adapt.translate_events import translate_events
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SetupFloodAdapt", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`SetupFloodAdapt` method."""

    sfincs_inp: Path | None = None
    """
    The file path to the SFINCS base model config file.
    """

    fiat_cfg: Path | None = None
    """
    The file path to the FIAT base model config file.
    """

    event_set_yaml: Path | None = None
    """
    The file path to the event set YAML file.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`SetupFloodAdapt` method."""

    fa_build_toml: Path
    """
    The file path to the flood adaptation model.
    """

    fiat_out_cfg: Path
    """The path to the copied fiat model configuration."""

    probabilistic_set: Path | None = None
    """The path to the event set configuration."""


class Params(Parameters):
    """Parameters for the :py:class:`SetupFloodAdapt` method."""

    output_dir: Path = Path("flood_adapt_builder")
    """
    The directory where the output files will be saved.
    """

    db_name: str = "fa_database"
    """
    The name of the FloodAdapt Database
    """

    description: str = "This is a FloodAdapt Database"
    """
    The description of the FloodAdapt Database
    """


class SetupFloodAdapt(Method):
    """Method for setting up the input for the FloodAdapt Database Builder.

    Parameters
    ----------
        sfincs_inp : Path
            The file path to the SFINCS base model.
        fiat_cfg : Path
            The file path to the FIAT base model.
        event_set_yaml : Path, optional
            The file path to the HydroFlows event set yaml file.
        output_dir: Path, optional
            The folder where the output is stored, by default "flood_adapt_builder".
        db_name: str, optional
            The name of the FloodAdapt Database
        description: str, optional
            The description of the FloodAdapt Database
        **params
            Additional parameters to pass to the GetERA5Rainfall instance.

    See Also
    --------
    :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.setup_flood_adapt.Input>`
    :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.setup_flood_adapt.Output>`
    :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.setup_flood_adapt.Params>`
    """

    name: str = "setup_flood_adapt"

    _test_kwargs = dict(
        sfincs_inp=Path("models", "sfincs", "sfincs.inp").as_posix(),
        fiat_cfg=Path("models", "fiat", "settings.toml").as_posix(),
        event_set_yaml=Path("data", "event_set", "event_set.yaml").as_posix(),
    )

    def __init__(
        self,
        sfincs_inp: Path | None = None,
        fiat_cfg: Path | None = None,
        event_set_yaml: Path | None = None,
        output_dir: Path = "flood_adapt_builder",
        db_name: str = "fa_database",
        description: str = "This is a FloodAdapt Database",
    ):
        self.input: Input = Input(
            sfincs_inp=sfincs_inp,
            fiat_cfg=fiat_cfg,
            event_set_yaml=event_set_yaml,
        )
        self.params: Params = Params(
            output_dir=output_dir, db_name=db_name, description=description
        )

        self.output: Output = Output(
            fa_build_toml=Path(self.params.output_dir, "fa_build.toml"),
            fiat_out_cfg=Path(self.params.output_dir, "fiat", "settings.toml"),
        )

        if self.input.event_set_yaml is not None:
            self.output.probabilistic_set = Path(
                self.params.output_dir,
                self.input.event_set_yaml.stem,
                f"{self.input.event_set_yaml.stem}.toml",
            )

    def _run(self):
        """Run the SetupFloodAdapt method."""
        # prepare and copy fiat model
        if self.input.fiat_cfg is not None:
            shutil.copytree(
                os.path.dirname(self.input.fiat_cfg),
                Path(self.params.output_dir, "fiat"),
                dirs_exist_ok=True,
                ignore=lambda d, c: {x for x in c if x.startswith("simulation")},
            )
        # prepare probabilistic set
        if self.input.event_set_yaml is not None:
            translate_events(
                self.input.event_set_yaml,
                Path(self.params.output_dir),
            )

            # Create FloodAdapt Database Builder config
            fa_db_config(
                self.params.output_dir,
                sfincs=self.input.sfincs_inp.parent.stem,
                db_name=self.params.db_name,
                description=self.params.description,
                probabilistic_set=self.input.event_set_yaml.stem,
            )

        else:
            # Create FloodAdapt Database Builder config
            fa_db_config(
                self.params.output_dir,
                sfincs=self.input.sfincs_inp.parent.stem,
                db_name=self.params.db_name,
                description=self.params.description,
            )

        pass


def fa_db_config(
    fa_root: Path,
    config: Path = Path(HYDROMT_CONFIG_DIR / "fa_database_build.yml"),
    sfincs: str = "sfincs",
    db_name: str = "fa_database",
    description: str = "This is a FloodAdapt Database",
    probabilistic_set: Path | None = None,
):
    """Create the path to the configuration file (.yml) that defines the settings.

    Parameters
    ----------
    config : Path
        The file path to the SFINCS base model.
    sfincs: str
        The name of the default sfincs model
    probabilistic_set : Path, optional
        The file path to the HydroFlows event set yaml file.
    """
    config = configread(config)
    config["sfincs"] = sfincs
    config["name"] = db_name
    config["description"] = description
    if probabilistic_set is not None:
        config["probabilistic_set"] = probabilistic_set
    with open(Path(fa_root, "fa_build.toml"), "w") as toml_file:
        toml.dump(config, toml_file)
