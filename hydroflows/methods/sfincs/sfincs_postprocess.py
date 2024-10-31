"""SFINCS postprocess method."""

from pathlib import Path
from typing import Optional

from hydromt_sfincs import SfincsModel

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsPostprocess"]


class Input(Parameters):
    """Input parameters for the :py:class:`SfincsPostprocess` method."""

    sfincs_map: Path
    """The path to the SFINCS model output sfincs_map.nc file."""


class Output(Parameters):
    """Output parameters for the :py:class:`SfincsPostprocess` method."""

    sfincs_zsmax: Path
    """The path to the output zsmax netcdf file."""


class Params(Parameters):
    """Parameters for the :py:class:`SfincsPostprocess` method."""

    output_root: Optional[Path] = None
    """The output directory where the hazard output files are saved."""

    file_name: str = "zsmax"
    """The name of the output file."""


class SfincsPostprocess(Method):
    """Reduce sfincs_map.nc zsmax variable to the global zsmax and save on a regular grid."""

    name: str = "sfincs_postprocess"

    _test_kwargs = {
        "sfincs_map": Path("sfincs_map.nc"),
    }

    def __init__(
        self,
        sfincs_map: Path,
        output_root: Optional[Path] = None,
        file_name: str = "zsmax",
    ) -> None:
        """Reduce sfincs_map.nc zsmax variable to the global zsmax and save on a regular grid.

        Parameters
        ----------
        sfincs_map : Path
            The path to the SFINCS model output sfincs_map.nc file.
        output_root : Optional[Path], optional
            The output directory where the hazard output files are saved.
            By default the output is saved in the same directory as the input.

        See Also
        --------
        :py:class:`sfincs_downscale Input <hydroflows.methods.sfincs.sfincs_downscale.Input>`
        :py:class:`sfincs_downscale Output <hydroflows.methods.sfincs.sfincs_downscale.Output>`
        :py:class:`sfincs_downscale Params <hydroflows.methods.sfincs.sfincs_downscale.Params>`
        """
        self.input: Input = Input(sfincs_map=sfincs_map)

        self.params: Params = Params(output_root=output_root, file_name=file_name)

        self.output: Output = Output(hazard_tif=output_root / self.params.file_name)

    def run(self):
        """Run the postprocessing."""
        # unpack input, output and params
        root = self.input.sfincs_map.parent
        sf = SfincsModel(root, mode="r", write_gis=False)

        # Read the model results
        sf.read_results()
        if "zsmax" not in sf.results:
            raise KeyError(f"zsmax is missing in results of {self.input.sfincs_map}")

        # get zsmax and save to file witt "water_level" as variable name
        zsmax = sf.results["zsmax"].max(dim="timemax").rename("water_level")
        zsmax.attrs["units"] = "m"
        zsmax.to_netcdf(
            self.output.sfincs_zsmax,
            encoding={"water_level": {"zlib": True, "complevel": 4}},
        )

        del sf
