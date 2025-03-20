"""Setup FloodAdapt method."""
import os
import shutil
from pathlib import Path

import toml
from hydromt.config import configread
from hydromt_sfincs import SfincsModel

from hydroflows._typing import FolderPath, OutPath
from hydroflows.config import HYDROMT_CONFIG_DIR
from hydroflows.methods.flood_adapt.translate_events import translate_events
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SetupFloodAdapt"]


class Input(Parameters):
    """Input parameters for the :py:class:`SetupFloodAdapt` method."""

    sfincs_inp: FolderPath
    """
    The file path to the SFINCS base model config file.
    """

    fiat_cfg: FolderPath
    """
    The file path to the FIAT base model config file.
    """

    event_set_yaml: FolderPath | None = None
    """
    The file path to the event set YAML file.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`SetupFloodAdapt` method."""

    fa_build_toml: Path
    """
    The file path to the flood adaptation model.
    """

    sfincs_out_inp: FolderPath
    """The path to the copied sfincs model configuration."""

    probabilistic_set: FolderPath | None = None
    """The path to the event set configuration."""


class Params(Parameters):
    """Parameters for the :py:class:`SetupFloodAdapt` method."""

    output_dir: OutPath = OutPath("flood_adapt_builder")
    """
    The directory where the output files will be saved.
    """


class SetupFloodAdapt(Method):
    """Rule for setting up the input for the FloodAdapt Database Builder."""

    name: str = "setup_flood_adapt"

    _test_kwargs = dict(
        sfincs_inp=Path("models", "sfincs", "sfincs.inp").as_posix(),
        fiat_cfg=Path("models", "fiat", "settings.toml").as_posix(),
        event_set_yaml=Path("data", "event_set", "event_set.yaml").as_posix(),
    )

    def __init__(
        self,
        sfincs_inp: Path,
        fiat_cfg: Path,
        event_set_yaml: Path | None = None,
        output_dir: Path = "flood_adapt_builder",
    ):
        """Create and validate a SetupFloodAdapt instance.

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
        **params
            Additional parameters to pass to the GetERA5Rainfall instance.

        See Also
        --------
        :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.setup_flood_adapt.Input>`
        :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.setup_flood_adapt.Output>`
        :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.setup_flood_adapt.Params>`
        """
        self.input: Input = Input(
            sfincs_inp=sfincs_inp,
            fiat_cfg=fiat_cfg,
            event_set_yaml=event_set_yaml,
        )
        self.params: Params = Params(output_dir=output_dir)

        self.output: Output = Output(
            fa_build_toml=Path(self.params.output_dir, "fa_build.toml"),
            sfincs_out_inp=Path(self.params.output_dir, "sfincs", "sfincs.inp"),
        )
        if self.input.event_set_yaml is not None:
            self.output.probabilistic_set = Path(
                self.params.output_dir,
                self.input.event_set_yaml.stem,
                f"{self.input.event_set_yaml.stem}.toml",
            )

    def _run(self):
        """Run the SetupFloodAdapt method."""
        # prepare and copy sfincs model
        shutil.copytree(
            os.path.dirname(self.input.sfincs_inp),
            Path(self.params.output_dir, "sfincs"),
            dirs_exist_ok=True,
        )
        if not Path(self.params.output_dir, "sfincs", "sfincs.bnd").exists():
            sm = SfincsModel(
                root=self.input.sfincs_inp.parent,
                mode="r",
            )
            x = sm.grid["x"].values
            y = sm.grid["y"].values
            sfincs_bnd = []
            sfincs_bnd.append(x[0])
            sfincs_bnd.append(y[0])
            with open(
                Path(self.params.output_dir, "sfincs", "sfincs.bnd"), "w"
            ) as output:
                for row in sfincs_bnd:
                    output.write(str(row) + " ")
            with open(
                Path(self.params.output_dir, "sfincs", "sfincs.inp"), "a"
            ) as sfincs_cfg:
                sfincs_cfg.write("bndfile = sfincs.bnd\n")

        if not Path(self.params.output_dir, "sfincs", "sfincs.bzs").exists():
            sfincs_bzs = [0, 0]
            with open(
                Path(self.params.output_dir, "sfincs", "sfincs.bzs"), "w"
            ) as output:
                for row in sfincs_bzs:
                    output.write(str(row) + " ")
            with open(
                Path(self.params.output_dir, "sfincs", "sfincs.inp"), "a"
            ) as sfincs_cfg:
                sfincs_cfg.write("bzsfile = sfincs.bzs\n")

        # prepare probabilistic set #NOTE: Is it possible to have multiple testsets in one workflow?
        if self.input.event_set_yaml is not None:
            translate_events(
                self.input.event_set_yaml,
                Path(self.params.output_dir),
            )

            # Create FloodAdapt Database Builder config
            fa_db_config(
                self.params.output_dir, probabilistic_set=self.input.event_set_yaml.stem
            )

        else:
            # Create FloodAdapt Database Builder config
            fa_db_config(self.params.output_dir)

        pass


def fa_db_config(
    fa_root: Path,
    config: Path = Path(HYDROMT_CONFIG_DIR / "fa_database_build.yml"),
    probabilistic_set: Path | None = None,
):
    """Create the path to the configuration file (.yml) that defines the settings.

    Parameters
    ----------
    config : Path
        The file path to the SFINCS base model.
    probabilistic_set : Path, optional
        The file path to the HydroFlows event set yaml file.
    """
    config = configread(config)
    if probabilistic_set is not None:
        config["probabilistic_set"] = probabilistic_set
    with open(Path(fa_root, "fa_build.toml"), "w") as toml_file:
        toml.dump(config, toml_file)
