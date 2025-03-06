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

    event_name: str
    """The name of the event, used to create the output filename."""


class SfincsPostprocess(Method):
    """Reduce sfincs_map.nc zsmax variable to the global zsmax and save on a regular grid."""

    name: str = "sfincs_postprocess"

    _test_kwargs = {
        "sfincs_map": Path("tests_event/sfincs_map.nc"),
    }

    def __init__(
        self,
        sfincs_map: Path,
        event_name: Optional[str] = None,
        output_root: Optional[Path] = None,
    ) -> None:
        """Reduce sfincs_map.nc zsmax variable to the global zsmax and save on a regular grid.

        output nc file is saved to {output_root}/zsmax_{event_name}.nc

        Parameters
        ----------
        sfincs_map : Path
            The path to the SFINCS model output sfincs_map.nc file.
        event_name : str
            The name of the event, used to create the output filename.
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

        if output_root is None:
            output_root = self.input.sfincs_map.parent
        if event_name is None:  # parent folder equals event name
            event_name = self.input.sfincs_map.parent.name
        self.params: Params = Params(output_root=output_root, event_name=event_name)

        # NOTE: unique output file name are required by HydroMT-FIAT hazard
        self.output: Output = Output(
            sfincs_zsmax=self.params.output_root / f"zsmax_{event_name}.nc"
        )

    def _run(self):
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
        zsmax = zsmax.fillna(-9999.0)
        zsmax.raster.set_nodata(-9999.0)
        zsmax.attrs["units"] = "m"
        zsmax.to_netcdf(
            self.output.sfincs_zsmax,
            encoding={"water_level": {"zlib": True, "complevel": 4}},
        )

        del sf
