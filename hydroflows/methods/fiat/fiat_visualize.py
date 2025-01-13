"""Module/ Rule for building FIAT models."""

import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
import toml
import tomli
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_write_metrics_file import MetricsFileWriter
from fiat_toolbox.metrics_writer.fiat_write_return_period_threshold import (
    ExceedanceProbabilityCalculator,
)
from pydantic import FilePath

from hydroflows.cfg import CFG_DIR
from hydroflows.events import EventSet
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["FIATVisualize"]


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`FIATVisualize` method.
    """

    fiat_cfg: Path
    """
    The file path to the output of the FIAT model.
    """

    event_set_file: Path
    """Path to the eventset cfg file."""


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`FIATVisualize` method.
    """

    fiat_infometrics: Path
    """The file path to the FIAT infometrics output."""

    fiat_infographics: Path
    """The file path to the FIAT infographics output."""


class Params(Parameters):
    """Parameters for the :py:class:`FIATVisualize`.

    Instances of this class are used in the :py:class:`FIATVisualize`
    method to define the required settings.

    See Also
    --------
    :py:class:`hydromt_fiat.fiat.FiatModel`
        For more details on the FiatModel used in hydromt_fiat.
    """

    output_dir: Path = ("models/fiat/fiat_metrics",)
    """The file path to the FIAT infometrics output."""

    aggregation: bool = False
    """Boolean to default aggregate or by aggregation area."""


class FIATVisualize(Method):
    """Rule for visualizing FIAT output."""

    name: str = "fiat_visualize"

    def __init__(
        self,
        fiat_cfg: Path,
        event_set_file: Path,
        output_dir: Path = "models/fiat/fiat_metrics",
        infographics_template: FilePath = CFG_DIR
        / "infographics"
        / "config_charts.toml",
        infometrics_template: FilePath = CFG_DIR
        / "infometrics"
        / "metrics_config.toml",
    ) -> None:
        """Create and validate a FIATVisualize instance.

        Parameters
        ----------
        fiat_cfg: Path
            The file path to the output of the FIAT model.
        event_set_file: Path
            The file path to the event set output of the hydromt SFINCS model.
        output_dir: Path = "models/fiat/fiat_metrics"
            The file path to the output of the FIAT infometrics and infographics.
        infographics_template: FilePath = CFG_DIR / "config_charts.toml"
            Path to the infographics template file.
        infometrics_template: FilePath = CFG_DIR / "metrics_config.toml"
            Path to the infometrics template file.

        See Also
        --------
        :py:class:`fiat_visualize Input <~hydroflows.methods.fiat.fiat_visualize.Input>`,
        :py:class:`fiat_visualize Output <~hydroflows.methods.fiat.fiat_visualize.Output>`,
        :py:class:`fiat_visualize Params <~hydroflows.methods.fiat.fiat_visualize.Params>`,
        :py:class:`hydromt_fiat.fiat.FIATModel`
        """
        self.params: Params = Params(output_dir=output_dir)
        self.input: Input = Input(
            fiat_cfg=fiat_cfg,
            event_set_file=event_set_file,
        )
        self.output: Output = Output(
            fiat_infometrics=self.params.output_dir
            / f"Infometrics_{self.input.event_set_file.stem}.csv",
            fiat_infographics=self.params.output_dir
            / f"{self.input.event_set_file.stem}_metrics.html",
        )

        self.infographics_template = infographics_template
        self.infometrics_template = infometrics_template

    def run(self):
        """Run the FIATVisualize method."""
        events = EventSet.from_yaml(self.input.event_set_file)
        rp = []
        event_set = EventSet(root=root, events=events.events)
        for event in event_set:
            return_period = 1 / event.return_period
        rp.append(return_period)
        scenario_name = events.stem

        # Write the metrics to file
        if events.mode == "risk":
            metrics_config = self.write_risk_infometrics_config(rp, self.input.fiat_cfg)
            self._add_exeedance_probability(
                self.input.fiat_cfg.parent / "output" / "output.csv", metrics_config
            )
        else:
            metrics_config = self.infometrics_template

        metrics_writer = MetricsFileWriter(metrics_config)
        infometrics_name = f"Infometrics_{(scenario_name)}.csv"
        metrics_full_path = metrics_writer.parse_metrics_to_file(
            df_results=pd.read_csv(
                self.input.fiat_cfg.parent / "output" / "output.csv"
            ),
            metrics_path=self.output.fiat_infometrics.parent.joinpath(infometrics_name),
            write_aggregate=None,
        )
        # Write aggregated metrics config files
        # for file in self.infometrics_template.parent.iterdir():
        #    with open(file, "r") as f:
        #        infometrics_cfg = toml.load(f)
        #    aggregation_areas = get_aggregation_areas(self.input.fiat_cfg.parent)
        #    aggr_names = []
        #    for aggregation_area in aggregation_areas:
        #        name = aggregation_area["name"]
        #        aggr_names.append(name)
        #    infometrics_cfg["aggregateBy"] = aggr_names
        #    with open(file, "w") as f:
        #        toml.dump(infometrics_cfg, f)

        # Write metrics
        metrics_writer.parse_metrics_to_file(
            df_results=pd.read_csv(
                self.input.fiat_cfg.parent / "output" / "output.csv"
            ),
            metrics_path=self.output.fiat_infometrics.parent.joinpath(infometrics_name),
            write_aggregate="all",
        )
        create_output_map(
            self.input.fiat_cfg.parent,
            self.input.event_set_file.stem,
            self.params.output_dir,
            aggregation_areas=get_aggregation_areas(self.input.fiat_cfg.parent),
        )

        # Write the infographic
        InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=events.mode,
            scenario_name=scenario_name,
            metrics_full_path=metrics_full_path,
            config_base_path=Path(self.infographics_template.parent),
            output_base_path=self.output.fiat_infographics.parent,
        ).write_infographics_to_file()

    def _add_exeedance_probability(self, fiat_results_path, config_path):
        """Add exceedance probability to the fiat results dataframe.

        Parameters
        ----------
        fiat_results_path : str
            Path to the fiat results csv file

        Returns
        -------
        pandas.DataFrame
        FIAT results dataframe with exceedance probability added
        """
        # Get config path

        with open(config_path, mode="rb") as fp:
            config = tomli.load(fp)["flood_exceedance"]

        # Check whether all configs are present
        if not all(key in config for key in ["column", "threshold", "period"]):
            raise ValueError("Not all required keys are present in the config file.")

        # Get the exceedance probability
        fiat_results_df = ExceedanceProbabilityCalculator(
            config["column"]
        ).append_to_file(
            fiat_results_path, fiat_results_path, config["threshold"], config["period"]
        )

        return fiat_results_df


def create_output_map(
    aggregation_areas: list,
    fiat_model: Path,
    event_set_file: str,
    fn_aggregated_metrics: Path = None,
):
    for aggregation_area in aggregation_areas:
        name = aggregation_area["name"]
        fn = aggregation_area["file"]
        field_name = aggregation_area["field_name"]
        gdf_aggregation = gpd.read_file(Path(fiat_model / fn))
        metrics_fn = Path(
            fn_aggregated_metrics
            / [f for f in os.listdir(fn_aggregated_metrics) if name in f][0]
        )
        metrics = pd.read_csv(metrics_fn, index_col=0).iloc[4:, 0:]
        metrics = metrics.sort_values(metrics.columns[0])
        metrics.reset_index(inplace=True, drop=True)
        gdf_new_aggr = gdf_aggregation.copy().sort_values(field_name)
        gdf_new_aggr.reset_index(inplace=True, drop=True)
        gdf_new_aggr[field_name] = metrics.iloc[0:, 0]

        for column in metrics.columns:
            if "TotalDamage" in column or "ExpectedAnnualDamages" in column:
                metrics_float = pd.to_numeric(metrics[column], errors="coerce")
                gdf_new_aggr[column] = metrics_float

        gdf_new_aggr.to_file(
            Path(
                fn_aggregated_metrics / f"{name}_total_damages_{event_set_file}.geojson"
            )
        )


def get_aggregation_areas(fiat_model):
    spatial_joins = toml.load(Path(fiat_model / "spatial_joins.toml"))
    aggregation_areas = spatial_joins["aggregation_areas"]
    return aggregation_areas


def write_risk_infometrics_config(rp: list, fiat_model: Path):
    """
    Write risk infometrics configuration file.

    Parameters
    ----------
    event_set_file : str
        Path to the event set file
    fiat_model : str
        Path to the FIAT model folder

    Returns
    -------
    config_risk_fn : str
        Path to the written risk infometrics configuration file

    Notes
    -----
    This function writes a risk infometrics configuration file based on the
    event set file and the FIAT model folder. The configuration file will
    contain the following metrics:

    - Expected annual damages
    - Homes likely to flood in 30-year period
    - Total damage with return periods of 2, 5, 10, 25, 50 and 100 years
    - Number of flooded residential, commercial and industrial buildings with
      return periods of 2, 5, 10, 25, 50 and 100 years

    The configuration file is written to the FIAT model folder with the name
    "metrics_config_risk.toml".
    """
    # Get aggregation area
    with open((fiat_model.parent / "spatial_joins.toml"), "r") as f:
        spatial_joins = toml.load(f)
    aggregation = spatial_joins["aggregation_areas"][0]["name"]
    x = 0
    # add mandatory metrics
    mandatory_metrics = mandatory_metrics = {
        "aggregateBy": [aggregation],
        "flood_exceedance": {"column": "inun_depth", "threshold": 0.2, "period": 30},
        "queries": [
            {
                "name": "ExpectedAnnualDamages",
                "description": "Expected annual damages",
                "select": "SUM('ead_damage')",
                "filter": "",
                "long_name": "Expected Annual Damages",
                "show_in_metrics_table": "True",
            },
            {
                "name": "FloodedHomes",
                "description": "Homes likely to flood (inun_depth > 0.2) in 30 year period",
                "select": "COUNT(*)",
                "filter": "'Exceedance Probability' > 50 AND 'primary_object_type' IN ('residential')",
                "long_name": "Homes likely to flood in 30-year period (#)",
                "show_in_metrics_table": "False",
            },
        ],
    }

    # add return period metrics
    while x < len(rp):
        config = {
            "name": f"TotalDamageRP{rp[x]}",
            "description": f"total_damage with return period of {rp[x]} years",
            "select": f"SUM(`total_damage_{rp[x]}.0y`)",
            "filter": "",
            "long_name": f"total_damage (RP {rp[x]})",
            "show_in_metrics_table": "True",
        }
        mandatory_metrics["queries"].append(config)
        x += 1

    x = 0
    while x < len(rp):
        config = {
            "name": f"FloodedHomes{rp[x]}Y",
            "description": f"Number of flooded residential buildings with return period of {rp[x]} years",
            "select ": "COUNT(*)",
            "filter": "`primary_object_type` IN (`residential`) AND `inun_depth_2.0y` > 0.2",
            "long_name": f"Flooded  homes (RP {rp[x]})",
            "show_in_metrics_table": "True",
        }
        mandatory_metrics["queries"].append(config)
        x += 1

    x = 0
    while x < len(rp):
        config = {
            "name": f"FloodedBusinesses{rp[x]}Y",
            "description": f"Number of flooded commercial buildings with return period of {rp[x]} years",
            "select": "COUNT(*)",
            "filter": "`primary_object_type` IN (`commercial`)  AND `inun_depth_2.0y` > 0.2",
            "long_name": f"Flooded  businesses (RP {rp[x]})",
            "show_in_metrics_table": "True",
        }
        mandatory_metrics["queries"].append(config)
        x += 1

    x = 0
    while x < len(rp):
        config = {
            "name": f":FloodedIndustry{rp[x]}Y",
            "description": f"Number of flooded industrial buildings with return period of {rp[x]} years",
            "select": "COUNT(*)",
            "filter": "`primary_object_type` IN (`industrial`) AND `inun_depth_2.0y` > 0.2",
            "long_name": f"Flooded  industry (RP {rp[x]})",
            "show_in_metrics_table": "True",
        }
        mandatory_metrics["queries"].append(config)
        x += 1

    # Write risk config file
    config_risk_fn = Path(fiat_model.parent / "metrics_config_risk.toml")

    with open(config_risk_fn, "w") as f:
        toml.dump(mandatory_metrics, f)

    return config_risk_fn
    print("done")
