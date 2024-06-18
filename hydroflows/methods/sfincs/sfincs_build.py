"""SFINCS build methods."""

from pathlib import Path

from hydromt.config import configread, configwrite
from hydromt.log import setuplog
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel, FilePath

from hydroflows._typing import ListOfStr
from hydroflows.methods.method import HYDROMT_CONFIG_DIR, Method

__all__ = ["SfincsBuild"]


class Input(BaseModel):
    """SfincsBuild input parameters."""

    region: FilePath
    """Path to the region vector file."""


class Output(BaseModel):
    """SfincsBuild output parameters."""

    sfincs_inp: Path
    """Path to the SFINCS input file."""

    sfincs_region: Path
    """Path to the SFINCS model region file."""


class Params(BaseModel):
    """SfincsBuild parameters."""

    data_libs: ListOfStr = ["artifact_data"]
    """List of data catalog files to use."""

    config: Path = Path(HYDROMT_CONFIG_DIR, "sfincs_build.yaml")
    """Path to the SFINCS build HydroMT configuration file."""

    res: float = 50.0
    """Resolution of the grid in meters."""

    river_upa: float = 30
    """Upstream area of the river in km2."""

    plot_fig: bool = True
    """Plot the basemap."""


class SfincsBuild(Method):
    """Method for building SFINCS models."""

    name: str = "sfincs_build"
    params: Params = Params()  # optional parameters
    input: Input
    output: Output

    def run(self):
        """Run the SFINCS build method."""
        # read the configuration
        opt = configread(self.params.config)
        # update placeholders in the config
        opt["setup_grid_from_region"].update(
            res=self.params.res, region={"geom": str(self.input.region)}
        )
        opt["setup_mask_active"].update(mask=str(self.input.region))
        # FIXME: because of the resolution of the grid and a small shift
        # of the merit hydro data the rivers do not align with the model domain
        # we should determine the river inflow points from the original region data?
        opt["setup_river_inflow"].update(river_upa=self.params.river_upa)
        # create the hydromt model
        root = self.output.sfincs_inp.parent
        sf = SfincsModel(
            root=root,
            mode="w+",
            data_libs=self.params.data_libs,
            logger=setuplog("sfincs_build", log_level=20),
        )
        # build the model
        sf.build(opt=opt)

        # write the opt as yaml
        configwrite(root / "sfincs_build.yaml", opt)

        # plot basemap
        if self.params.plot_fig == True:
            sf.plot_basemap(fn_out="basemap.png", plot_region=False, shaded=False)
