"""Get GTSM data method."""

from datetime import datetime
from pathlib import Path

import geopandas as gpd
from hydromt.data_catalog import DataCatalog

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["GetGTSMData"]


class Input(Parameters):
    """Input parameters for the :py:class:`GetGTSMData` method."""

    region: Path
    """
    Path to file containing area of interest geometry.
    Centroid is used to look for nearest GTSM station.
    """

    gtsm_catalog: Path
    """Path to HydroMT data catalog describing GTSM data."""


class Output(Parameters):
    """Output parameters for the :py:class:`GetGTSMData` method."""

    waterlevel_nc: Path
    """Path to output file containing waterlevel .nc timeseries"""

    surge_nc: Path
    """Path to output file containing surge .nc timeseries"""

    tide_nc: Path
    """Path to output file containing tide .nc timeseries"""

    bnd_locations: Path
    """Path to output file containing point locations associated with the timeseries."""


class Params(Parameters):
    """Params for the :py:class:`GetGTSMData` method."""

    data_root: Path = Path("data/input")

    start_time: datetime = datetime(1979, 1, 1)
    """Start date for the fetched timeseries"""

    end_time: datetime = datetime(2018, 12, 31)
    """End date for the fetched timeseries"""

    catalog_key: str = "gtsm_codec_reanalysis_10min_v1"
    """Data catalog key for GTSM data."""


class GetGTSMData(Method):
    """Method for getting GTSM waterlevel and surge timeseries at centroid of a region.

    See Also
    --------
    :py:function:`hydroflows.methods.coastal.get_gtsm_data.get_gtsm_station`
    :py:function:`hydroflows.methods.coastal.get_gtsm_data.export_gtsm_data`
    """

    name: str = "get_gtsm_data"

    _test_kwargs = {
        "region": "region.geojson",
        "gtsm_catalog": "data_catalog.yml",
    }

    def __init__(
        self,
        region: Path,
        gtsm_catalog: Path,
        data_root: Path = Path("data/input"),
        **params,
    ) -> None:
        """Create and validate a GetGTSMData instance.

        Parameters
        ----------
        region : Path
            Path to file containing area of interest geometry.
            Centroid is used to look for nearest GTSM station.
        data_root : Path, optional
            The root folder where data is stored, by default "data/input/forcing_data/waterlevel"

        See Also
        --------
        :py:class:`Input <hydroflows.methods.coastal.get_gtsm_data.Input>`
        :py:class:`Input <hydroflows.methods.coastal.get_gtsm_data.Output>`
        :py:class:`Input <hydroflows.methods.coastal.get_gtsm_data.Params>`
        """
        self.input: Input = Input(region=region, gtsm_catalog=gtsm_catalog)
        self.params: Params = Params(data_root=data_root, **params)

        waterlevel_path = self.params.data_root / "gtsm_waterlevel.nc"
        surge_path = self.params.data_root / "gtsm_surge.nc"
        tide_path = self.params.data_root / "gtsm_tide.nc"
        bnd_locations = self.params.data_root / "gtsm_locations.gpkg"
        self.output: Output = Output(
            waterlevel_nc=waterlevel_path,
            surge_nc=surge_path,
            tide_nc=tide_path,
            bnd_locations=bnd_locations,
        )

    def run(self):
        """Run GetGTSMData method."""
        region = gpd.read_file(self.input.region).to_crs(4326)
        dc = DataCatalog(data_libs=self.input.gtsm_catalog)
        gtsm = dc.get_geodataset(
            self.params.catalog_key,
            geom=region,
            time_tuple=(self.params.start_time, self.params.end_time),
        )

        s = gtsm["surge"]
        h = gtsm["waterlevel"]
        t = (h - s).rename("tide")
        t.attrs.update({"short_name": "tide"})
        if "unit" in h.attrs:
            t.attrs.update({"unit": h.attrs["unit"]})

        s.to_netcdf(self.output.surge_nc)
        t.to_netcdf(self.output.tide_nc)
        h.to_netcdf(self.output.waterlevel_nc)

        gtsm.vector.to_gdf().to_file(self.output.bnd_locations, driver="GPKG")
