"""SFINCS postprocess method."""

from pathlib import Path
from typing import Optional

from hydromt_sfincs import SfincsModel, utils

from hydroflows._typing import JsonDict
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["SfincsPostprocess"]


class Input(Parameters):
    """Input parameters for the :py:class:`SfincsPostprocess` method."""

    sfincs_map: Path
    """The path to the SFINCS model output sfincs_map.nc file."""

    sfincs_subgrid_dep: Path
    """The path to the highres dem file to use for downscaling the results."""


class Output(Parameters):
    """Output parameters for the :py:class:`SfincsPostprocess` method."""

    hazard_tif: Path
    """The path to the output inundation raster geotiff."""


class Params(Parameters):
    """Parameters for the :py:class:`SfincsPostprocess` method."""

    hazard_root: Path
    """The path to the root directory where the hazard output files are saved."""

    event_name: str
    """The name of the event."""

    depth_min: float = 0.05
    """Minimum depth to consider as "flooding."""

    raster_kwargs: JsonDict = {}
    """Kwargs to pass to writer of inundation raster."""


class SfincsPostprocess(Method):
    """Rule for postprocessing Sfincs output to an inundation map."""

    name: str = "sfincs_postprocess"

    _test_kwargs = {
        "sfincs_map": Path("sfincs_map.nc"),
        "sfincs_subgrid_dep": Path("subgrid/dep_subgrid.tif"),
    }

    def __init__(
        self,
        sfincs_map: Path,
        sfincs_subgrid_dep: Path,
        event_name: Optional[str] = None,
        hazard_root: Path = "data/output/hazard",
        **params,
    ) -> None:
        """Create and validate a SfincsPostprocess instance.

        Parameters
        ----------
        sfincs_map : Path
            The path to the SFINCS model output sfincs_map.nc file.
        sfincs_subgrid_dep : Path
            The path to the highres dem file to use for downscaling the results.
        hazard_root : Path, optional
            The path to the root directory where the hazard output files are saved,
            by default "data/output/hazard".
        **params
            Additional parameters to pass to the SfincsPostprocess instance.
            See :py:class:`sfincs_postprocess Params <hydroflows.methods.sfincs.sfincs_postprocess.Params>`.

        See Also
        --------
        :py:class:`sfincs_postprocess Input <hydroflows.methods.sfincs.sfincs_postprocess.Input>`
        :py:class:`sfincs_postprocess Output <hydroflows.methods.sfincs.sfincs_postprocess.Output>`
        :py:class:`sfincs_postprocess Params <hydroflows.methods.sfincs.sfincs_postprocess.Params>`
        """
        self.input: Input = Input(
            sfincs_map=sfincs_map, sfincs_subgrid_dep=sfincs_subgrid_dep
        )

        if event_name is None:  # event name is the stem of the event file
            event_name = self.input.sfincs_map.parent.stem
        self.params: Params = Params(
            hazard_root=hazard_root, event_name=event_name, **params
        )

        self.output: Output = Output(
            hazard_tif=self.params.hazard_root / f"{event_name}.tif"
        )

    def run(self):
        """Run the postprocessing from SFINCS netcdf to inundation map."""
        # unpack input, output and params
        root = self.input.sfincs_map.parent
        sfincs_subgrid_dep = self.input.sfincs_subgrid_dep
        hazard_file = self.output.hazard_tif
        hmin = self.params.depth_min

        sf = SfincsModel(root, mode="r", write_gis=False)
        dep = sf.data_catalog.get_rasterdataset(sfincs_subgrid_dep)

        # Read the model results
        sf.read_results()
        if "zsmax" not in sf.results:
            raise KeyError(f"zsmax is missing in results of {self.input.sfincs_map}")

        # Extract maximum water levels per time step from subgrid model
        zsmax = sf.results["zsmax"]

        # compute the maximum over all time steps
        zsmax = zsmax.max(dim="timemax")

        # Fourthly, downscale the floodmap
        utils.downscale_floodmap(
            zsmax=zsmax,
            dep=dep,
            hmin=hmin,
            floodmap_fn=hazard_file,
            **self.params.raster_kwargs,
        )
