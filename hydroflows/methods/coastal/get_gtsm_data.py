"""Get GTSM data method."""

import glob
import platform
from datetime import datetime
from pathlib import Path
from shutil import rmtree

import geopandas as gpd
import pandas as pd
import xarray as xr

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["GetGTSMData"]

PDRIVE = "p:/" if platform.system() == "Windows" else "/p/"
GTSM_ROOT = Path(
    PDRIVE, "archivedprojects", "11205028-c3s_435", "01_data", "01_Timeseries"
)


class Input(Parameters):
    """Input parameters for the :py:class:`GetGTSMData` method."""

    region: Path
    """
    Path to file containing area of interest geometry.
    Centroid is used to look for nearest GTSM station.
    """


class Output(Parameters):
    """Output parameters for the :py:class:`GetGTSMData` method."""

    waterlevel_nc: Path
    """Path to output file containing waterlevel .nc timeseries"""

    surge_nc: Path
    """Path to output file containing surge .nc timeseries"""

    tide_nc: Path
    """Path to output file containing tide .nc timeseries"""


class Params(Parameters):
    """Params for the :py:class:`GetGTSMData` method."""

    data_root: Path = Path("data/input")

    start_time: datetime = datetime(1979, 1, 1)
    """Start date for the fetched timeseries"""

    end_time: datetime = datetime(2018, 12, 31)
    """End date for the fetched timeseries"""

    timestep: str = "10min"
    """Time step of the output timeseries"""

    # TODO: Do something about hard coded ref to p-drive
    gtsm_loc: Path = GTSM_ROOT
    """
    Location of GTSM data.
    Points to internal Deltares storage by default.
    """


class GetGTSMData(Method):
    """Method for getting GTSM waterlevel and surge timeseries at centroid of a region.

    See Also
    --------
    :py:function:`hydroflows.methods.coastal.get_gtsm_data.get_gtsm_station`
    :py:function:`hydroflows.methods.coastal.get_gtsm_data.export_gtsm_data`
    """

    name: str = "get_gtsm_data"

    def __init__(
        self,
        region: Path,
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
        self.input: Input = Input(region=region)
        self.params: Params = Params(data_root=data_root, **params)

        waterlevel_path = self.params.data_root / "gtsm_waterlevel.nc"
        surge_path = self.params.data_root / "gtsm_surge.nc"
        tide_path = self.params.data_root / "gtsm_tide.nc"
        self.output: Output = Output(
            waterlevel_nc=waterlevel_path, surge_nc=surge_path, tide_nc=tide_path
        )

    def run(self):
        """Run GetGTSMData method."""
        gdf = gpd.read_file(self.input.region).to_crs(4326)
        stations = get_gtsm_station(gdf, self.params.gtsm_loc / "gtsm_locs.gpkg")
        # stations = get_gtsm_station(
        #     gdf.centroid.x, gdf.centroid.y, self.params.gtsm_loc / "gtsm_locs.gpkg"
        # )
        stations = stations["stations"].values

        variables = {
            "s": {
                "var": "surge",
                "stations": stations,
                "outpath": self.output.surge_nc,
            },
            "h": {
                "var": "waterlevel",
                "stations": stations,
                "outpath": self.output.waterlevel_nc,
            },
        }

        for var, kwargs in variables.items():
            print(f"Downloading {var} data")
            fn_out = export_gtsm_data(
                outdir=self.output.waterlevel_nc.parent,
                tstart=datetime.strftime(self.params.start_time, "%Y-%m-%d"),
                tend=datetime.strftime(self.params.end_time, "%Y-%m-%d"),
                data_path=self.params.gtsm_loc
                / r"*2/{var}/reanalysis_{var}_{dt}_{year}_*_v1.nc",
                dt=self.params.timestep,
                # var=var,
                **kwargs,
            )

        rmtree(fn_out.parent / "gtsm_tmp")
        s = xr.open_dataarray(self.output.surge_nc)
        h = xr.open_dataarray(self.output.waterlevel_nc)
        t = h - s
        t.to_netcdf(self.output.tide_nc)


def get_gtsm_station(
    # x: float,
    # y: float,
    region: gpd.GeoDataFrame,
    stations_fn: Path,
) -> gpd.GeoDataFrame:
    """Return GTSM station closest to query location.

    Parameters
    ----------
    x : float
        Query location x coordinate
    y : float
        Query location y coordinate
    stations_fn : Path
        Path to file containing GTSM station coordinates

    Returns
    -------
    gpd.GeoDataFrame
        GTSM station ID and coordinates
    """
    gdf = gpd.read_file(stations_fn).drop_duplicates(subset="geometry")
    # idx = gdf.sindex.nearest(Point(x, y))[1]
    # return gdf.iloc[idx]
    return gdf.clip(region)


def export_gtsm_data(
    outdir: Path,
    stations: list,
    data_path: Path,
    tstart: str,
    tend: str,
    dt: str,
    var: str,
    outpath: str,
    chunks: dict = None,
) -> Path:
    """Return GTSM data variable timeseries in a single file.

    Parameters
    ----------
    outdir : Path
        Destination folder of timeseries file
    stations : list
        GTSM station to fetch data at
    data_path : Path
        GTSM data location
    tstart : str
        Start time of output timeseries
    tend : str
        End time of output timeseries
    dt : str
        Time step of output timeseries. One of [10min, hourly, dailymax]
    var : str
        GTSM data variable
    fn_out : str
        Output file name
    chunks : _type_, optional
        xarray open_mfdataset chunking option when reading GTSM data files, by default {"stations": 1}

    Returns
    -------
    Path
        Path to output timeseries .nc file
    """
    if chunks is None:
        chunks = {"stations": 1}

    units = {
        "surge": "m",
        "waterlevel": "m+MSL",
    }

    def _filter(ds, stations=stations):
        return ds.sel(stations=stations)

    tmpdir = outdir / "gtsm_tmp"
    if not tmpdir.exists():
        tmpdir.mkdir(parents=True)

    ts = pd.date_range(tstart, tend, freq="YS")
    encoding = {var: {"dtype": "float32", "zlib": True}}
    for t in ts:
        fns = glob.glob(data_path.as_posix().format(var=var, dt=dt, year=t.year))
        fn_out = tmpdir / f"{var}_{t.year}.nc"
        if fn_out.exists() or len(fns) == 0:
            continue

        da = xr.open_mfdataset(fns, chunks=chunks, preprocess=_filter)[var].load()
        da.attrs.update({"long_name": var, "units": units.get(var, "-")})
        da.to_netcdf(fn_out, encoding=encoding)

    fns = glob.glob(str(tmpdir / f"{var}_*.nc"))
    fn_out = outpath
    # if len(fns) > 1:
    ds = xr.open_mfdataset(fns).load()
    ds.to_netcdf(fn_out, encoding=encoding)
    ds.close()

    return fn_out
