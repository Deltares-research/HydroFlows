"""SFINCS downscale method."""

from pathlib import Path
from typing import Optional

from hydromt_sfincs import SfincsModel, utils

from hydroflows._typing import FolderPath, JsonDict, OutPath
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsDownscale"]


class Input(Parameters):
    """Input parameters for the :py:class:`SfincsDownscale` method."""

    sfincs_map: FolderPath
    """The path to the SFINCS model output sfincs_map.nc file."""

    sfincs_subgrid_dep: Path
    """The path to the highres dem file to use for downscaling the results."""


class Output(Parameters):
    """Output parameters for the :py:class:`SfincsDownscale` method."""

    hazard_tif: Path
    """The path to the output inundation raster geotiff."""


class Params(Parameters):
    """Parameters for the :py:class:`SfincsDownscale` method."""

    output_root: Optional[OutPath] = None
    """The path to the root directory where the hazard output files are saved."""

    event_name: str
    """The name of the event, used to create the output filename."""

    depth_min: float = 0.05
    """Minimum depth to consider as "flooding."""

    raster_kwargs: JsonDict = {}
    """Kwargs to pass to writer of inundation raster."""


class SfincsDownscale(Method):
    """Rule for downscaling Sfincs output to an inundation map."""

    name: str = "sfincs_downscale"

    _test_kwargs = {
        "sfincs_map": Path("test_event/sfincs_map.nc"),
        "sfincs_subgrid_dep": Path("subgrid/dep_subgrid.tif"),
    }

    def __init__(
        self,
        sfincs_map: Path,
        sfincs_subgrid_dep: Path,
        event_name: Optional[str] = None,
        output_root: Optional[Path] = None,
        **params,
    ) -> None:
        """Downscale SFINCS waterlevels to a flood depth map.

        output tif file is saved to {output_root}/hmax_{event_name}.tif

        Parameters
        ----------
        sfincs_map : Path
            The path to the SFINCS model output sfincs_map.nc file.
        sfincs_subgrid_dep : Path
            The path to the highres dem file to use for downscaling the results.
        event_name : str
            The name of the event, used to create the output filename.
        output_root : Optional[Path], optional
            The output directory where the hazard output files are saved.
            By default the output is saved in the same directory as the input.
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

        if output_root is None:
            output_root = self.input.sfincs_map.parent
        if event_name is None:  # parent folder equals event name
            event_name = self.input.sfincs_map.parent.name
        self.params: Params = Params(
            output_root=output_root, event_name=event_name, **params
        )

        # NOTE: unique output file name are required by HydroMT-FIAT hazard
        self.output: Output = Output(
            hazard_tif=Path(output_root, f"hmax_{self.params.event_name}.tif")
        )

    def _run(self):
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
