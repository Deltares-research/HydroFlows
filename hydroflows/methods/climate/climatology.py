"""Module for gridded statistics of climate data, wip."""

import inspect
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, model_validator

from hydroflows._typing import FolderPath, ListOfListOfInt, ListOfStr, OutPath
from hydroflows.io import to_netcdf
from hydroflows.methods.climate.grid_utils import extract_climate_projections_statistics
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`MonthlyClimatolgy` method.
    """

    region: Path
    """
    The Path to the region vector file.
    """

    catalog_path: FolderPath | None
    """
    The file path to the data catalog. Should contain the the `clim_source` data.
    """


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`MonthlyClimatolgy` method.
    """

    climatology: Path
    """
    The path to the dataset containing the climate factors.
    """


class Params(Parameters):
    """Parameters for the :py:class:`MonthlyClimatolgy`.

    Instances of this class are used in the :py:class:`MonthlyClimatolgy`
    method to define the required settings.
    """

    model_config = ConfigDict(extra="allow")

    predefined_catalogs: ListOfStr | None = None
    """List of predefined catalogs to use."""

    clim_source: Literal["cmip6", "cmip5", "isimip3"] = "cmip6"
    """The source of the climate data (e.g. 'cmip6', 'cmip5', 'isimip3').
    Must be one of the available sources in the catalog_path."""

    members: ListOfStr = ["r1i1p1f1"]
    """List of member names of the climate model (e.g. r1i1p1f1).
    Depends on the climate source."""

    model: str
    """Model name of the climate model (e.g. 'NOAA-GFDL_GFDL-ESM4', 'INM_INM-CM5-0').
    Depends on the climate source."""

    scenario: str
    """Scenario name of the climate model (e.g. historical, ssp245, ssp585).
    Depends on the climate source."""

    horizon: ListOfListOfInt
    """The horizon of the future scenario (e.g. [[2090, 2100]])."""

    output_dir: OutPath = OutPath("data", "climatology")
    """The output directory of the climatology dataset."""

    @model_validator(mode="after")
    def check_model_extra_fields(self):
        """Check if the model_extra fields are in the signature of extract_climate_projections_statistics."""
        if self.model_extra is not None:
            par = set(
                inspect.signature(
                    extract_climate_projections_statistics
                ).parameters.keys()
            )
        for key in self.model_extra:
            if key not in par:
                raise ValueError(f"Parameter {key} unknown, use one of {par}.")
        return self


class MonthlyClimatolgy(Method):
    """Method for gridded monthly climatology of the climate model."""

    name: str = "monthly_climatology"

    _test_kwargs = {
        "region": Path("region.geojson"),
        "catalog_path": "data_catalog.yml",
        "model": "NOAA-GFDL_GFDL-ESM4",
        "scenario": "ssp585",
        "horizon": [[2090, 2100]],
        "output_dir": Path("data", "input", "stats"),
        "pet_method": "Makkink",  # test extra field
    }

    def __init__(
        self,
        region: Path,
        model: str,
        scenario: str,
        horizon: ListOfListOfInt,
        catalog_path: Path | None = None,
        output_dir: Path = Path("data", "climatology"),
        **params,
    ) -> None:
        """Create monthly climatology from climate model data.

        Parameters
        ----------
        region : Path
           Path to the region vector file.
        catalog_path : Path
            Path to the data catalog. Should contain the the `clim_source` data.
        model : str
            Model name of the climate model (e.g. 'NOAA-GFDL_GFDL-ESM4', 'INM_INM-CM5-0').
            Depends on the climate source.
        scenario : str
            Scenario name of the climate model (e.g. historical, ssp245, ssp585).
            Depends on the climate source.
        horizon : ListOfListOfInt
            The horizon(s) of the future scenario (e.g. [[2090, 2100]]).
        output_dir : Path
            The output directory of the climatology dataset.
        **params
            Additional parameters to pass to the MonthlyClimatolgy instance.
            See :py:class:`climatology Params <hydroflows.methods.climate.climatology.Params>`.

        See Also
        --------
        :py:class:`climatology Input <~hydroflows.methods.climate.climatology.Input>`
        :py:class:`climatology Output <~hydroflows.methods.climate.climatology.Output>`
        :py:class:`climatology Params <~hydroflows.methods.climate.climatology.Params>`
        """
        self.input: Input = Input(region=region, catalog_path=catalog_path)
        if (
            self.input.catalog_path is None
            and params.get("predefined_catalogs") is None
        ):
            params["predefined_catalogs"] = ["gcs_cmip6_data"]
        self.params: Params = Params(
            model=model,
            scenario=scenario,
            horizon=horizon,
            output_dir=output_dir,
            **params,
        )
        # post-fix required to avoid ambiguity in snakemake
        pf = "_future" if self.params.scenario != "historical" else ""
        file_name = f"climatology_{self.params.model}_{self.params.scenario}{pf}.nc"
        self.output: Output = Output(
            climatology=self.params.output_dir / file_name,
        )

    def _run(self) -> None:
        """Run the gridded climate statistics method."""
        # Prepare the time horizon dictionary
        horizons = [[str(i) for i in item] for item in self.params.horizon]
        if self.params.scenario == "historical":
            time_horizon = {self.params.scenario: horizons[0]}
        else:
            horizon_fmt = ["-".join(item) for item in horizons]
            time_horizon = dict(zip(horizon_fmt, horizons))

        # Prepare the data libraries
        data_libs = (
            self.params.predefined_catalogs if self.input.catalog_path is None else []
        )
        if self.input.catalog_path is not None:
            data_libs.append(self.input.catalog_path)

        # Execute the function
        stats_ds = extract_climate_projections_statistics(
            self.input.region,
            data_libs=data_libs,
            clim_source=self.params.clim_source,
            members=self.params.members,
            model=self.params.model,
            scenario=self.params.scenario,
            time_horizon=time_horizon,
            **self.params.model_extra,
        )

        # Save to drive
        to_netcdf(
            stats_ds,
            file_name=self.output.climatology.name,
            output_dir=self.output.climatology.parent,
        )
