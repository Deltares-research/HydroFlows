"""Sfincs postprocess method."""

from pathlib import Path

from hydromt_sfincs import SfincsModel, utils
from pydantic import BaseModel, FilePath

from hydroflows.method import Method

__all__ = ["SfincsPostprocess"]


class Input(BaseModel):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`SfincsPostprocess` method.
    """

    sfincs_inp: FilePath
    sfincs_dep: FilePath


class Output(BaseModel):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`SfincsPostprocess` method.
    """

    sfincs_inun: Path


class Params(BaseModel):
    """Parameters.

    Instances of this class are used in the :py:class:`SfincsPostprocess`
    method to define the required settings.
    """

    depth_min: float = 0.05
    """Minimum depth to consider as "flooding."""

    raster_kwargs: dict = {}
    """Kwargs to pass to writer of inundation raster."""


class SfincsPostprocess(Method):
    """Rule for postprocessing Sfincs output to an inundation map.

    This class utilizes the :py:class:`Params <hydroflows.methods.sfincs.sfincs_postprocess.Params>`,
    :py:class:`Input <hydroflows.methods.sfincs.sfincs_postprocess.Input>`, and
    :py:class:`Output <hydroflows.methods.sfincs.sfincs_postprocess.Output>` classes to run
    the postprocessing from the Sfincs netcdf to generate an inundation map.
    """

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
            floodmap_fn=fn_inun,
            **self.params.raster_kwargs,
        )

    @classmethod
    def from_input_args(
        cls, sfincs_map: Path, dem: Path, flood_map: Path, **params
    ) -> "SfincsPostprocess":
        """Create a new instance from input arguments.

        Parameters
        ----------
        sfincs_map : Path
            Path to the SFINCS map nc output file.
        dem : Path
            Path to the a high resolution DEM.
        flood_map : Path
            Path to the output flood map.
        **params : dict
            Additional parameters.

        Returns
        -------
        SfincsPostprocess
        """
        input = {
            "sfincs_map": sfincs_map,
            "dem": dem,
        }
        output = {
            "flood_map": flood_map,
        }
        return cls(input=input, output=output, params=params)
