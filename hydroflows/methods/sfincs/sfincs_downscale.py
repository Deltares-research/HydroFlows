"""SFINCS downscale method."""

from pathlib import Path
from typing import Optional

from hydromt_sfincs import SfincsModel, utils

from hydroflows._typing import JsonDict
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsDownscale"]


class Input(Parameters):
    """Input parameters for the :py:class:`SfincsDownscale` method."""

    sfincs_map: Path
    """The path to the SFINCS model output sfincs_map.nc file."""

    sfincs_subgrid_dep: Path
    """The path to the highres dem file to use for downscaling the results."""


class Output(Parameters):
    """Output parameters for the :py:class:`SfincsDownscale` method."""

    hazard_tif: Path
    """The path to the output inundation raster geotiff."""


class Params(Parameters):
    """Parameters for the :py:class:`SfincsDownscale` method."""

    output_root: Optional[Path] = None
    """The path to the root directory where the hazard output files are saved."""

    file_name: str = "hmax"
    """The name of the event."""

    depth_min: float = 0.05
    """Minimum depth to consider as "flooding."""

    raster_kwargs: JsonDict = {}
    """Kwargs to pass to writer of inundation raster."""


class SfincsDownscale(Method):
    """Rule for downscaling Sfincs output to an inundation map."""

    name: str = "sfincs_downscale"

    _test_kwargs = {
        "sfincs_map": Path("sfincs_map.nc"),
        "sfincs_subgrid_dep": Path("subgrid/dep_subgrid.tif"),
    }

    def __init__(
        self,
        sfincs_map: Path,
        sfincs_subgrid_dep: Path,
        output_root: Optional[Path] = None,
        file_name: str = "hmax",
        **params,
    ) -> None:
        """Downscale SFINCS waterlevels to a flood depth map.

        Parameters
        ----------
        sfincs_map : Path
            The path to the SFINCS model output sfincs_map.nc file.
        sfincs_subgrid_dep : Path
            The path to the highres dem file to use for downscaling the results.
        hazard_root : Path, optional
            The path to the root directory where the hazard output files are saved,
            by default the same directory as the sfincs_map files.
        file_name : str, optional
            The name of the output file, by default "hmax".
        **params
            Additional parameters to pass to the SfincsDownscale instance.
            See :py:class:`sfincs_downscale Params <hydroflows.methods.sfincs.sfincs_downscale.Params>`.

        See Also
        --------
        :py:class:`sfincs_downscale Input <hydroflows.methods.sfincs.sfincs_downscale.Input>`
        :py:class:`sfincs_downscale Output <hydroflows.methods.sfincs.sfincs_downscale.Output>`
        :py:class:`sfincs_downscale Params <hydroflows.methods.sfincs.sfincs_downscale.Params>`
        """
        self.input: Input = Input(
            sfincs_map=sfincs_map, sfincs_subgrid_dep=sfincs_subgrid_dep
        )

        self.params: Params = Params(
            output_root=output_root, file_name=file_name, **params
        )

        output_root = self.params.output_root or self.input.sfincs_map.parent
        self.output: Output = Output(
            hazard_tif=Path(output_root, f"{self.params.file_name}.tif")
        )

    def run(self):
        """Run the downscaling from SFINCS waterlevels to a flood depth map."""
        # unpack input, output and params
        root = self.input.sfincs_map.parent
        hazard_file = self.output.hazard_tif

        sf = SfincsModel(root, mode="r", write_gis=False)
        dep = sf.data_catalog.get_rasterdataset(self.input.sfincs_subgrid_dep)

        # Read the model results
        sf.read_results()
        if "zsmax" not in sf.results:
            raise KeyError(f"zsmax is missing in results of {self.input.sfincs_map}")

        # get zsmax
        zsmax = sf.results["zsmax"].max(dim="timemax")
        zsmax.attrs["units"] = "m"

        # save to file
        utils.downscale_floodmap(
            zsmax=zsmax,
            dep=dep,
            hmin=self.params.depth_min,
            floodmap_fn=hazard_file,
            **self.params.raster_kwargs,
        )

        del sf
