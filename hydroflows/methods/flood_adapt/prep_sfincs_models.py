"""Setup FloodAdapt method."""
import shutil
from pathlib import Path

from hydromt_sfincs import SfincsModel

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["PrepSfincsModels"]


class Input(Parameters):
    """Input parameters for the :py:class:`PrepSfincsModels` method."""

    sfincs_inp: Path
    """
    The file path to the SFINCS base model config file.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`PrepSfincsModels` method."""

    sfincs_out_inp: Path
    """The path to the copied sfincs model configuration."""


class Params(Parameters):
    """Parameters for the :py:class:`PrepSfincsModels` method."""

    output_dir: Path = Path("flood_adapt_builder")
    """
    The directory where the output files will be saved.
    """


class PrepSfincsModels(Method):
    """Rule for setting up the sfincs models for the FloodAdapt Database Builder."""

    name: str = "prep_sfincs_models"

    _test_kwargs = dict(sfincs_inp=Path("models", "sfincs", "sfincs.inp").as_posix())

    def __init__(
        self,
        sfincs_inp: Path,
        output_dir: Path = "flood_adapt_builder",
    ):
        """Create and validate a PrepSfincsModels instance.

        Parameters
        ----------
        sfincs_inp : Path
            The file path to the SFINCS base model.
        output_dir: Path, optional
            The folder where the output is stored, by default "flood_adapt_builder".
        **params
            Additional parameters to pass to the GetERA5Rainfall instance.

        See Also
        --------
        :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.sprep_sfincs_models.Input>`
        :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.prep_sfincs_models.Output>`
        :py:class:`SetupFloodAdapt Input <hydroflows.methods.flood_adapt.prep_sfincs_models.Params>`
        """
        self.input: Input = Input(
            sfincs_inp=sfincs_inp,
        )
        self.params: Params = Params(output_dir=output_dir)

        self.output: Output = Output(
            sfincs_out_inp=Path(
                self.params.output_dir, self.input.sfincs_inp.parent.stem, "sfincs.inp"
            ),
        )

    def _run(self):
        """Run the PrepSfincsModels method."""
        # Get all sfincs models and prepare and copy sfincs model
        sfincs_model = Path(self.params.output_dir, self.input.sfincs_inp.parent.stem)
        shutil.copytree(
            Path(self.input.sfincs_inp.parent.parent / self.input.sfincs_inp.parent),
            sfincs_model,
            dirs_exist_ok=True,
        )
        sm = SfincsModel(
            root=sfincs_model,
            mode="r",
        )

        if "bndfile" not in sm.config:
            sm.setup_waterlevel_bnd_from_mask(10000)
            sm.write_forcing()
            sm.config.pop("bzsfile")
            Path(sfincs_model, "sfincs.bzs").unlink()

        # Remove discharge
        if "disfile" in sm.config:
            Path(sfincs_model, "sfincs.dis").unlink()
            sm.config.pop("disfile")
            sm.write_config()

        # Remove simulation and figure folder
        if Path(sfincs_model, "simulations").exists():
            shutil.rmtree(Path(sfincs_model, "simulations"))
        if Path(sfincs_model, "figs").exists():
            shutil.rmtree(Path(sfincs_model, "figs"))

        # Remove discharge
        if Path(sfincs_model, "sfincs.dis").exists():
            Path(sfincs_model, "sfincs.dis").unlink()
            sm.config.pop("disfile")
        # Remove simulation and figure folder
        if Path(sfincs_model, "simulations").exists():
            shutil.rmtree(Path(sfincs_model, "simulations"))
        if Path(sfincs_model, "figs").exists():
            shutil.rmtree(Path(sfincs_model, "figs"))
