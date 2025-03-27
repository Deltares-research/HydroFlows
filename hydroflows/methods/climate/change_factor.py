"""Method for calculating future change factors."""

from pathlib import Path

from hydroflows._typing import ListOfListOfInt
from hydroflows.methods.climate.grid_utils import get_expected_change_grid
from hydroflows.methods.utils.io import to_netcdf
from hydroflows.workflow.method import ExpandMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["ClimateChangeFactors", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`ClimateChangeFactors` method.
    """

    hist_climatology: Path
    """Path to the dataset with historical climate statistics."""

    future_climatology: Path
    """Path to the dataset with future climate statistics."""


class Output(Parameters):
    """output parameters.

    this class represents the output data
    generated by the :py:class:`ClimateChangeFactors` method.
    """

    change_factors: Path
    """Path to the file containing the gridded climate change factors."""


class Params(Parameters):
    """Parameters for the :py:class:`ClimateChangeFactors`.

    Instances of this class are used in the :py:class:`ClimateChangeFactors`
    method to define the required settings.
    """

    model: str
    """
    The specific climate model to be merged (e.g. 'NOAA-GFDL_GFDL-ESM4', 'INM_INM-CM5-0').
    """

    scenario: str
    """
    The specific climate scenario to be merged (e.g. historical, ssp245, ssp585).
    """

    horizon: ListOfListOfInt
    """
    The horizon of the future scenario (e.g. [[2090, 2100]]).
    """

    wildcard: str = "horizons"
    """
    Name of the wildcard.
    """

    convert_to_fraction: bool = True
    """
    Whether or not to convert the change factors from percentages to fractions.
    """

    output_dir: Path
    """
    The output directory of the dataset.
    """


class ClimateChangeFactors(ExpandMethod):
    """Create gridded climate change factors from monthly climatology.

    Parameters
    ----------
    hist_climatology : Path
        Path to the file with historical climate climatology.
    future_climatology : Path
        Path to the file with future climate climatology.
    model : str
        Model name of the climate model (e.g. 'NOAA-GFDL_GFDL-ESM4', 'INM_INM-CM5-0').
        Depends on the climate source.
    scenario : str
        Scenario name of the climate model (e.g. historical, ssp245, ssp585).
        Depends on the climate source.
    horizon : ListOfListOfInt
        The horizon of the future scenario (e.g. [[2090, 2100]]).
    output_dir : Path
        The output directory of the change factor dataset.
    **params
        Additional parameters to pass to the ClimateChangeFactors instance.
        See :py:class:`change_factor Params <hydroflows.methods.climate.change_factor.Params>`.

    See Also
    --------
    :py:class:`change_factor Input <hydroflows.methods.climate.change_factor.Input>`
    :py:class:`change_factor Output <hydroflows.methods.climate.change_factor.Output>`
    :py:class:`change_factor Params <hydroflows.methods.climate.change_factor.Params>`
    """

    name: str = "climate_change_factors"

    _test_kwargs = {
        "hist_climatology": Path("hist_climatology.nc"),
        "future_climatology": Path("future_climatology.nc"),
        "model": "NOAA-GFDL_GFDL-ESM4",
        "scenario": "ssp585",
        "horizon": [[2090, 2100]],
        "output_dir": Path("data/climatology"),
    }

    def __init__(
        self,
        hist_climatology: Path,
        future_climatology: Path,
        model: str,
        scenario: str,
        horizon: ListOfListOfInt,
        output_dir: Path = Path("data", "climatology"),
        **params,
    ) -> None:
        self.params: Params = Params(
            model=model,
            scenario=scenario,
            horizon=horizon,
            output_dir=output_dir,
            **params,
        )
        self.input: Input = Input(
            hist_climatology=hist_climatology, future_climatology=future_climatology
        )
        wc = f"{{{self.params.wildcard}}}"
        self.output: Output = Output(
            change_factors=self.params.output_dir
            / f"change_{self.params.model}_{self.params.scenario}_{wc}.nc"
        )
        self.formatted_wildcards = [
            "-".join([str(i) for i in item]) for item in self.params.horizon
        ]
        self.set_expand_wildcard(
            self.params.wildcard,
            values=self.formatted_wildcards,
        )

    def _run(self):
        """Run the climate factors gridded method."""
        for wc in self.formatted_wildcards:
            # NOTE Expected change is absolute [°C] for temperature and dew point temperature,
            # and relative [%] for all others.
            change_ds = get_expected_change_grid(
                nc_historical=self.input.hist_climatology,
                nc_future=self.input.future_climatology,
                name_horizon=wc,
            )

            # convert from percentage to fraction for variables that are not temperature
            if self.params.convert_to_fraction:
                for var in change_ds.data_vars:
                    if var.startswith("temp"):
                        continue
                    change_ds[var] = 1 + change_ds[var] / 100
                    change_ds[var].attrs["long_name"] = f"fraction change in {var}"
                    change_ds[var].attrs["units"] = "-"

            output = self.get_output_for_wildcards({self.params.wildcard: wc})
            nc_path = output["change_factors"]
            to_netcdf(change_ds, file_name=nc_path.name, output_dir=nc_path.parent)
