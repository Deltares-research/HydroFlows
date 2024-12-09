import os
import shutil
from pathlib import Path

import toml

from hydroflows.methods.flood_adapt.translate_events import translate_events
from hydroflows.methods.flood_adapt.translate_FIAT import translate_model
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SetupFloodAdapt"]


class Input(Parameters):
    sfincs_base_model: Path
    """
    The file path to the SFINCS base model.
    """

    fiat_base_model: Path
    """
    The file path to the FIAT base model.
    """

    event_set_yaml: Path | None = None
    """
    The file path to the event set YAML file.
    """


class Params(Parameters):
    output_dir: Path = Path("flood_adapt_builder")
    """
    The directory where the output files will be saved.
    """


class Output(Parameters):
    fa_build_toml: Path
    """
    The file path to the flood adaptation model.
    """

    fiat_input: Path
    """The path to the translated FIAT model configuration."""

    sfincs_input: Path
    """The path to the copied sfincs model configuration."""

    probabilistic_set: Path | None = None
    """The path to the event set configuration."""


class SetupFloodAdapt(Method):
    """Rule for setting up the input for the FloodAdapt Database Builder."""

    name: str = "setup_flood_adapt"

    def __init__(
        self,
        sfincs_base_model: Path,
        fiat_base_model: Path,
        event_set_yaml: Path | None = None,
        output_dir: Path = "flood_adapt_builder",
    ):
        """Create and validate a SetupFloodAdapt instance.

        Parameters
        ----------
        sfincs_base_model : Path
            The file path to the SFINCS base model.
        fiat_base_model : Path
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
        self.input = Input(
            sfincs_base_model=sfincs_base_model,
            fiat_base_model=fiat_base_model,
            event_set_yaml=event_set_yaml,
        )
        self.params = Params(output_dir=output_dir)

        self.output = Output(
            fa_build_toml=Path(self.params.output_dir, "fa_build.toml"),
            fiat_input=Path(self.params.output_dir, "fiat", "settings.toml"),
            sfincs_input=Path(self.params.output_dir, "sfincs", "sfincs.inp"),
        )
        if self.input.event_set_yaml is not None:
            self.output.probabilistic_set = Path(
                self.params.output_dir, "events", "probabilistic_set.toml"
            )

    def run(self):
        """Run the SetupFloodAdapt method."""
        # prepare fiat model
        translate_model(
            self.input.fiat_base_model, Path(self.params.output_dir, "fiat")
        )

        # prepare and copy sfincs model
        shutil.copytree(
            self.input.sfincs_base_model,
            Path(self.params.output_dir, "sfincs"),
            dirs_exist_ok=True,
        )

        # prepare probabilistic set
        if self.input.event_set_yaml is not None:
            translate_events(
                self.input.event_set_yaml,
                Path(self.params.output_dir, "events"),
                "probabilistic_set",
            )

            # Create FloodAdapt Database Builder config
            fa_db_config(probabilistic_set="events")

        else:
            # Create FloodAdapt Database Builder config
            fa_db_config()

        pass


def fa_db_config(
    output_dir: Path = "flood_adapt_builder",
    database_path: Path = "Database/flood_adapt_db",
    fiat_config: Path = "fiat",
    sfincs_config: Path = "sfincs",
    probabilistic_set: Path | None = None,
):
    """Create a TOML configuration file for the FloodAdapt Database Builder.

    Parameters
    ----------
    output_dir : Path, optional
        The directory where the output file will be saved, by default "flood_adapt_builder".
    database_path : Path, optional
        The path to the FloodAdapt database, by default "flood_adapt_db".
    fiat_config : Path, optional
        The path to the FIAT configuration, by default "fiat".
    sfincs_config : Path, optional
        The path to the SFINCS configuration, by default "sfincs".
    probabilistic_set : Path | None, optional
        The path to the probabilistic event set configuration, by default None.
    """
    databasebuilder_config = {
        "name": "fa_database",
        "database_path": database_path,
        "sfincs": sfincs_config,
        "fiat": fiat_config,
        "unit_system": "metric",  # TODO: hard coded or input parameter?
        "gui": {
            "max_flood_depth": 2,  # TODO: hard coded or input parameter?
            "max_aggr_dmg": 10000000,  # TODO: hard coded or input parameter?
            "max_footprint_dmg": 250000,  # TODO: hard coded or input parameter?
            "max_benefits": 50000000,  # TODO: hard coded or input parameter?
        },
    }
    if probabilistic_set is not None:
        databasebuilder_config["probabilistic_set"] = probabilistic_set

    with open(Path(output_dir, "fa_build.toml"), "w") as toml_file:
        toml.dump(databasebuilder_config, toml_file)
