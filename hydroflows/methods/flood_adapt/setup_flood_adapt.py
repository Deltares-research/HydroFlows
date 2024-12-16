"""Setup FloodAdapt method."""
import os
import shutil
from pathlib import Path

import geopandas as gpd
import toml
from hydromt.config import configread

from hydroflows.config import HYDROMT_CONFIG_DIR
from hydroflows.methods.flood_adapt.translate_events import translate_events
from hydroflows.methods.flood_adapt.translate_FIAT import translate_model
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SetupFloodAdapt"]


class Input(Parameters):
    """Input parameters for the :py:class:`SetupFloodAdapt` method."""

    sfincs_inp: Path
    """
    The file path to the SFINCS base model config file.
    """

    fiat_cfg: Path
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
    """The path to the translated FIAT model configuration."""

    sfincs_out_inp: Path
    """The path to the copied sfincs model configuration."""

    probabilistic_set: Path | None = None
    """The path to the event set configuration."""


class Params(Parameters):
    """Parameters for the :py:class:`SetupFloodAdapt` method."""

    output_dir: Path = Path("flood_adapt_builder")
    """
    The directory where the output files will be saved.
    """


class SetupFloodAdapt(Method):
    """Rule for setting up the input for the FloodAdapt Database Builder."""

    name: str = "setup_flood_adapt"

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
            fiat_out_cfg=Path(self.params.output_dir, "fiat", "settings.toml"),
            sfincs_out_inp=Path(self.params.output_dir, "sfincs", "sfincs.inp"),
        )
        if self.input.event_set_yaml is not None:
            self.output.probabilistic_set = Path(
                self.params.output_dir, "probabilistic_set", "probabilistic_set.toml"
            )

    def run(self):
        """Run the SetupFloodAdapt method."""
        # prepare fiat model
        translate_model(
            os.path.dirname(self.input.fiat_cfg),
            Path(self.params.output_dir, "fiat"),
        )

        # prepare and copy sfincs model
        shutil.copytree(
            os.path.dirname(self.input.sfincs_inp),
            Path(self.params.output_dir, "sfincs"),
            dirs_exist_ok=True,
        )
        if not Path(self.params.output_dir, "sfincs", "sfincs.bnd").exists():
            region = self.input.fiat_cfg.parent / "geoms" / "region.geojson"
            sfincs_bnd_region = gpd.read_file(region)
            sfincs_bnd = []
            sfincs_bnd_x = sfincs_bnd_region.centroid[0].x
            sfincs_bnd_y = sfincs_bnd_region.centroid[0].y
            sfincs_bnd = [sfincs_bnd_x, sfincs_bnd_y]
            with open(
                Path(self.params.output_dir, "sfincs", "sfincs.bnd"), "w"
            ) as output:
                for row in sfincs_bnd:
                    output.write(str(row) + " ")

        if not Path(self.params.output_dir, "sfincs", "sfincs.bzs").exists():
            sfincs_bzs = [0, 0]
            with open(
                Path(self.params.output_dir, "sfincs", "sfincs.bzs"), "w"
            ) as output:
                for row in sfincs_bzs:
                    output.write(str(row) + " ")

        # prepare probabilistic set #NOTE: Is it possible to have multiple testsets in one workflow?
        if self.input.event_set_yaml is not None:
            translate_events(
                self.input.event_set_yaml,
                Path(self.params.output_dir, "probabilistic_set"),
            )

            # Create FloodAdapt Database Builder config
            fa_db_config(probabilistic_set=self.output.probabilistic_set)

        else:
            # Create FloodAdapt Database Builder config
            fa_db_config()

        pass


def fa_db_config(
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
        config["probabilistic_set"] = probabilistic_set.as_posix()

    with open(Path("flood_adapt_builder", "fa_build.toml"), "w") as toml_file:
        toml.dump(config, toml_file)
