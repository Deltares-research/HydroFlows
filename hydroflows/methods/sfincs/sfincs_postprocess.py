"""Sfincs postprocess method."""

from pathlib import Path

from hydromt_sfincs import SfincsModel, utils
from pydantic import BaseModel

from hydroflows.methods.method import Method

__all__ = ["SfincsPostprocess"]


class Input(BaseModel):
    """Input parameters for the :py:class:`SfincsPostprocess` method."""

    sfincs_map: Path
    """The path to the SFINCS model output sfincs_map.nc file."""

    dem_file: Path
    """The path to the highres dem file to use for downscaling the results."""


class Output(BaseModel):
    """Output parameters for the :py:class:`SfincsPostprocess` method."""

    hazard_tif: Path
    """The path to the output inundation raster geotiff."""


class Params(BaseModel):
    """Parameters for the :py:class:`SfincsPostprocess` method."""

    hazard_root: Path
    """The path to the root directory where the hazard output files are saved."""

    depth_min: float = 0.05
    """Minimum depth to consider as "flooding."""

    raster_kwargs: dict = {}
    """Kwargs to pass to writer of inundation raster."""


class SfincsPostprocess(Method):
    """Rule for postprocessing Sfincs output to an inundation map."""

    name: str = "sfincs_postprocess"

    def __init__(
        self,
        sfincs_map: Path,
        dem_file: Path = None,
        hazard_root: Path = "data/output/hazard",
        **params,
    ) -> None:
        """Create and validate a SfincsPostprocess instance.

        Parameters
        ----------
        sfincs_map : Path
            The path to the SFINCS model output sfincs_map.nc file.
        dem_file : Path, optional
            The path to the highres dem file to use for downscaling the results.
            By default None and set to the subgrid/dep.tif file in the SFINCS basemodel folder.
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
        # params: Params = Params() # optional parameters
        self.params: Params = Params(hazard_root=hazard_root, **params)

        if dem_file is None:
            # assume basemodel is two levels up from sfincs_map
            basemodel_root = Path(sfincs_map).parent.parent.parent
            dem_file = basemodel_root / "subgrid" / "dep.tif"
        self.input: Input = Input(sfincs_map=sfincs_map, dem_file=dem_file)

        # set the output file;
        # NOTE: we assume the sfincs_map parent folder is the event name
        event_name = Path(sfincs_map).parent.stem
        hazard_tif = self.params.hazard_root / f"{event_name}.tif"
        self.output: Output = Output(hazard_tif=hazard_tif)

        # TODO create output event file

    def run(self):
        """Run the postprocessing from SFINCS netcdf to inundation map."""
        # check if the input files and the output directory exist
        self.check_input_output_paths()

        # unpack input, output and params
        root = self.input.sfincs_map.parent
        dem_file = self.input.dem_file
        hazard_file = self.output.hazard_tif
        hmin = self.params.depth_min

        sf = SfincsModel(root, mode="r", write_gis=False)
        dep = sf.data_catalog.get_rasterdataset(dem_file)

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
