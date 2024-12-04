from pathlib import Path

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

    fiat_config: Path

    sfincs_input: Path

    probabilistic_set: Path | None = None


class SetupFloodAdapt(Method):
    name: str = "setup_flood_adapt"

    def __init__(
        self,
        sfincs_base_model: Path,
        fiat_base_model: Path,
        event_set_yaml: Path | None = None,
        output_dir: Path = "flood_adapt_builder",
    ):
        self.input = Input(
            sfincs_base_model=sfincs_base_model,
            fiat_base_model=fiat_base_model,
            event_set_yaml=event_set_yaml,
        )
        self.params = Params(output_dir=output_dir)

        self.output = Output(
            fa_build_toml=Path(self.params.output_dir, "fa_build.toml"),
            fiat_config=Path(self.params.output_dir, "fiat", "settings.toml"),
            sfincs_input=Path(self.params.output_dir, "sfincs", "sfincs.inp"),
        )
        if self.input.event_set_yaml is not None:
            self.output.probabilistic_set = Path(
                self.params.output_dir, "events", "probabilistic_set.toml"
            )

    def run(self):
        # prepare fiat model

        # prepare and copy sfincs model

        # prepare probabilistic set

        pass
