"""Method for fetching and processing COAST-RP dataset for a given region."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import xarray as xr
from hydromt.data_catalog import DataCatalog

from hydroflows._typing import FolderPath, OutPath
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["GetCoastRP", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`GetCoastRP` method."""

    region: Path
    """Path to region geometry file."""

    coastrp_catalog: FolderPath
    """Path to full COAST-RP dataset."""


class Output(Parameters):
    """Output parameters for the :py:class:`GetCoastRP` method."""

    rps_nc: Path
    """Path to return period and values dataset."""


class Params(Parameters):
    """Params parameters for the :py:class:`GetCoastRP` method."""

    data_root: OutPath = OutPath("data/input/forcing_data/waterlevel")
    """The folder root where output is stored."""

    catalog_key: str = "coast-rp"
    """Data catalog key for COAST-RP data."""

    buffer: float = 2000
    """Buffer around region to look for GTSM stations, [m]"""


class GetCoastRP(Method):
    """Method for fetching and processing COAST-RP dataset for a given region.

    Parameters
    ----------
    region : Path
        Path to region geometry file.
        Centroid is used to look for closest station to be consistent with GetGTSMData method.
    coastrp_fn : Path
        Path to full COAST-RP dataset.
    data_root : Path, optional
        The folder root where output is stored, by default "data/input/forcing_data/waterlevel"

    See Also
    --------
    :py:class:`GetCoastRP Input <hydroflows.methods.coastal.get_coast_rp.Input>`
    :py:class:`GetCoastRP Output <hydroflows.methods.coastal.get_coast_rp.Output>`
    :py:class:`GetCoastRP Params <hydroflows.methods.coastal.get_coast_rp.Params>`
    """

    name: str = "get_coast_rp"

    _test_kwargs = {
        "region": "region.geojson",
        "coastrp_catalog": "data_catalog.yml",
    }

    def __init__(
        self,
        region: Path,
        coastrp_catalog: Path,
        data_root: Path = Path("data/input/forcing_data/waterlevel"),
        **params,
    ) -> None:
        self.input: Input = Input(region=region, coastrp_catalog=coastrp_catalog)
        self.params: Params = Params(data_root=data_root, **params)

        rps_fn = self.params.data_root / "waterlevel_rps.nc"
        self.output: Output = Output(rps_nc=rps_fn)

    def _run(self) -> None:
        """Run GetCoastRP Method."""
        region = gpd.read_file(self.input.region)
        dc = DataCatalog(data_libs=self.input.coastrp_catalog)
        coast_rp = dc.get_geodataset(
            self.params.catalog_key, geom=region, buffer=self.params.buffer
        )
        coast_rp = xr.concat(
            [coast_rp[var] for var in coast_rp.data_vars if var != "station_id"],
            dim=pd.Index([1, 2, 5, 10, 25, 50, 100, 250, 500, 1000], name="rps"),
        ).to_dataset(name="return_values")
        coast_rp.to_netcdf(self.output.rps_nc)
