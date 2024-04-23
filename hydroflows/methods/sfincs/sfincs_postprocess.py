"""Sfincs postprocess method."""

from pathlib import Path

from hydromt_sfincs import SfincsModel, utils
from pydantic import BaseModel, FilePath

from ..method import Method

__all__ = ["SfincsPostprocess"]

class Input(BaseModel):
    """Input parameters."""

    sfincs_inp: FilePath
    sfincs_dep: FilePath


class Output(BaseModel):
    """Output parameters."""

    sfincs_inun: Path

class Params(BaseModel):
    """Parameters."""

    depth_min: float = 0.05  # minimum depth to consider as "flooding"
    raster_kwargs: dict = {}  # kwargs to pass to writer of inundation raster

class SfincsPostprocess(Method):
    """Rule for postprocessing Sfincs."""

    name: str = "sfincs_postprocess"
    # params: Params = Params() # optional parameters
    input: Input
    output: Output
    params: Params = Params()

    def run(self):
        """Run the postprocessing from SFINCS netcdf to inundation map."""
        root = self.input.sfincs_inp.parent
        fn_dep = self.input.sfincs_dep
        fn_inun = self.output.sfincs_inun
        hmin = self.params.depth_min

        sf = SfincsModel(root, mode="r", write_gis=False)
        dep = sf.data_catalog.get_rasterdataset(fn_dep)

        # Read the model results
        sf.read_results()
        if "zsmax" not in sf.results:
            raise KeyError(f"zsmax is missing in results of {self.input.sfincs_inp}")

        # Extract maximum water levels per time step from subgrid model
        zsmax = sf.results["zsmax"]

        # compute the maximum over all time steps
        zsmax = zsmax.max(dim='timemax')

        # Fourthly, downscale the floodmap
        utils.downscale_floodmap(
            zsmax=zsmax,
            dep=dep,
            hmin=hmin,
            floodmap_fn=fn_inun,
            kwargs=self.params.raster_kwargs
        )
