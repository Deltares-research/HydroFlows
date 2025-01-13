"""Module for gridded statistics of climate data, wip."""

from pathlib import Path

from hydroflows._typing import ListOfListOfInt, ListOfPath, ListOfStr
from hydroflows.methods.climate.grid_utils import extract_climate_projections_statistics
from hydroflows.methods.climate.utils import to_netcdf
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`ClimateStatistics` method.
    """

    region: Path
    """
    The Path to the region vector file.
    """


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`ClimateStatistics` method.
    """

    stats: Path
    """
    The path to the dataset containing the climate factors.
    """


class Params(Parameters):
    """Parameters for the :py:class:`ClimateStatistics`.

    Instances of this class are used in the :py:class:`ClimateStatistics`
    method to define the required settings.
    """

    data_libs: ListOfPath | ListOfStr
    """List of data libraries to be used. This is a predefined data catalog in
    yml format, which should contain the data sources specified in the config file."""

    model: str
    """
    The specific climate model to be used. Chose e.g. ... # TODO
    """

    scenario: str = None
    """
    The specific climate scenario. Chose from ... # TODO
    """

    horizon: ListOfListOfInt
    """
    The horizon of the future scenario.
    """

    data_root: Path
    """
    The output directory of the dataset.
    """


class ClimateStatistics(Method):
    """Method for gridded statistics of the climate model."""

    name: str = "climate_statistics"

    _test_kwargs = {
        "region": Path("region.geojson"),
        "data_libs": ["data_catalog.yml"],
        "model": "NOAA-GFDL_GFDL-ESM4",
        "scenario": "ssp585",
        "horizon": [[2090, 2100]],
        "data_root": Path("data", "input", "stats"),
    }

    def __init__(
        self,
        region: Path,
        **params,
    ) -> None:
        """Create statistics from climate data.

        Parameters
        ----------
        region : Path
           Path to the region vector file.
        **params
            Additional parameters to pass to the ClimateStatistics instance.
            See :py:class:`grid_stats Params <hydroflows.methods.climate.grid_stats.Params>`.

        See Also
        --------
        :py:class:`grid_stats Input <~hydroflows.methods.climate.grid_stats.Input>`
        :py:class:`grid_stats Output <~hydroflows.methods.climate.grid_stats.Output>`
        :py:class:`grid_stats Params <~hydroflows.methods.climate.grid_stats.Params>`
        """
        self.params: Params = Params(**params)
        self.input: Input = Input(region=region)
        name = "historical"
        self.scenario = name
        elements = ["stats", self.params.model]
        if self.params.scenario is not None:
            name = "future"
            self.scenario = self.params.scenario
            elements.append(self.params.scenario)
        elements.append(name)
        self.out_file = "_".join(elements) + ".nc"
        self.output: Output = Output(
            stats=self.params.data_root / self.out_file,
        )

    def run(self) -> None:
        """Run the gridded climate statistics method."""
        # Prepare the time horizon dictionary
        horizons = [[str(i) for i in item] for item in self.params.horizon]
        if self.params.scenario is None:
            time_horizon = {self.scenario: horizons[0]}
        else:
            horizon_fmt = ["-".join(item) for item in horizons]
            time_horizon = dict(zip(horizon_fmt, horizons))

        # Execute the function
        stats_ds = extract_climate_projections_statistics(
            self.input.region,
            data_catalog=self.params.data_libs,
            scenario=self.scenario,
            clim_source="cmip6",
            members=["r1i1p1f1"],
            model=self.params.model,
            variables=["precip", "temp", "pet"],
            pet_method="makkink",
            tdew_method="sh",
            compute_wind=False,
            time_horizon=time_horizon,
        )

        # Save to drive
        to_netcdf(
            stats_ds,
            file_name=self.out_file,
            output_dir=self.params.data_root,
        )
