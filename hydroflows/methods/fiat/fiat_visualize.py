"""Module/ Rule for building FIAT models."""

import os
import shutil
from pathlib import Path
from typing import Optional

import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import toml
import tomli
from fiat_toolbox.infographics.infographics_factory import InforgraphicFactory
from fiat_toolbox.metrics_writer.fiat_write_metrics_file import MetricsFileWriter
from fiat_toolbox.metrics_writer.fiat_write_return_period_threshold import (
    ExceedanceProbabilityCalculator,
)
from pydantic import DirectoryPath, FilePath

from hydroflows.cfg import CFG_DIR
from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["FIATVisualize"]


class Input(Parameters):
    """Input parameters.

    This class represents the input data
    required for the :py:class:`FIATVisualize` method.
    """

    fiat_output_csv: Path
    """
    The file path to the output.csv file of the FIAT model.
    """

    spatial_joins_cfg: Path = "models/fiat/spatial_joins.toml"
    """The path to the spatial joins configuration file."""

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file from the FIAT model simulation."""


class Params(Parameters):
    """Parameters for the :py:class:`FIATBuild`.

    Instances of this class are used in the :py:class:`FIATBuild`
    method to define the required settings.

    See Also
    --------
    :py:class:`hydromt_fiat.fiat.FiatModel`
        For more details on the FiatModel used in hydromt_fiat.
    """

    infographics_template: FilePath = Path(
        CFG_DIR, "infographics", "config_charts.toml"
    )
    """The path to the infographics template file."""

    infographics_template_risk: FilePath = Path(
        CFG_DIR, "infographics", "config_risk_charts.toml"
    )
    """The path to the infographics template file."""

    infometrics_template: FilePath = Path(CFG_DIR, "infometrics", "metrics_config.toml")
    """The path to the infometrics template file."""

    infographic_images: DirectoryPath = CFG_DIR / "infographics" / "images"
    """The path to the directory where the images for the infographics are saved."""

    output_dir: Path = Path("output/fiat")
    """The path to the directory where the infometrics and infographics output can be saved."""

    scenario_name: str
    """The name of the simulation scenario."""


class Output(Parameters):
    """Output parameters.

    This class represents the output data
    generated by the :py:class:`FIATVisualize` method.
    """

    fiat_infometrics: Path
    """The file path to the FIAT infometrics output."""

    fiat_infographics: Path
    """The file path to the FIAT infographics output."""


class FIATVisualize(Method):
    """Rule for visualizing FIAT output."""

    name: str = "fiat_visualize"

    _test_kwargs = {
        "infometrics_template": Path(CFG_DIR, "infometrics", "metrics_config.toml"),
        "infographics_template_risk": Path(
            CFG_DIR, "infographics", "config_charts_risk.toml"
        ),
        "infographics_template": Path(CFG_DIR, "infographics", "config_charts.toml"),
        "infographic_images": CFG_DIR / "infographics" / "images",
    }

    def __init__(
        self,
        fiat_output_csv: Path,
        fiat_cfg: Path,
        scenario_name: Optional[str] = None,
        spatial_joins_cfg: Path = "models/fiat/spatial_joins.toml",
        output_dir: Path = Path("output/fiat"),
        **params,
    ) -> None:
        """Create and validate a FIATVisualize instance.

        Parameters
        ----------
        fiat_output_csv: Path
            The file path to the output csv of the FIAT model.
        fiat_cfg: Path
            The file path to the FIAT configuration (toml) file from the FIAT model simulation.
        spatial_joins_cfg: Path = "models/fiat/spatial_joins.toml"
            The path to the spatial joins configuration file.
        **params
            Additional parameters to pass to the FIATVisualize instance.
            See :py:class:`fiat_visualize Params <hydroflows.methods.fiat.fiat_visualize.Params>`.

        See Also
        --------
        :py:class:`fiat_visualize Input <~hydroflows.methods.fiat.fiat_visualize.Input>`,
        :py:class:`fiat_visualize Output <~hydroflows.methods.fiat.fiat_visualize.Output>`,
        :py:class:`fiat_visualize Params <~hydroflows.methods.fiat.fiat_visualize.Params>`,
        :py:class:`hydromt_fiat.fiat.FIATModel`
        """
        self.input: Input = Input(
            spatial_joins_cfg=spatial_joins_cfg,
            fiat_output_csv=fiat_output_csv,
            fiat_cfg=fiat_cfg,
        )
        if scenario_name is None:
            scenario_name = str(self.input.fiat_cfg.parent.stem)
        self.params: Params = Params(
            output_dir=output_dir, scenario_name=scenario_name, **params
        )
        self.output: Output = Output(
            fiat_infometrics=self.params.output_dir
            / f"Infometrics_{self.params.scenario_name}.csv",
            fiat_infographics=self.params.output_dir
            / f"{self.params.scenario_name}_metrics.html",
        )

    def run(self):
        """Run the FIATVisualize method."""
        # Get return periods
        config = toml.load(self.input.fiat_cfg)
        if (
            "return_periods" in config["hazard"].keys()
        ):  # NOTE Is there always rp in settings.toml and just empty for single event?
            rp = config["hazard"]["return_periods"]
            mode = "risk"
        else:
            mode = "single_event"
        # Get infographic images
        Path(self.input.fiat_output_csv.parent / "images").mkdir(exist_ok=True)
        for png_file in Path(self.params.infographic_images).glob("*.png"):
            shutil.copy(
                png_file,
                Path(self.input.fiat_output_csv.parent / "images"),
            )

        # Write the metrics to file
        if mode == "risk":
            infographics_template = self.params.infographics_template_risk
            metrics_config, config_charts = write_risk_infometrics_config(
                rp,
                fiat_model=self.input.spatial_joins_cfg.parent,
                output_folder=self.input.fiat_output_csv.parent,
                infographics_template=infographics_template,
            )

            self._add_exeedance_probability(
                self.input.fiat_output_csv.parent / "output.csv", metrics_config
            )
            metrics_writer = MetricsFileWriter(
                Path(self.input.fiat_output_csv.parent / "infometrics_config_risk.toml")
            )
        else:
            infographics_template = self.params.infographics_template
            with open(self.params.infometrics_template, "r") as f:
                infometrics_cfg = toml.load(f)
            aggregation_areas = get_aggregation_areas(self.input.spatial_joins_cfg)
            aggr_names = []
            for aggregation_area in aggregation_areas:
                name = aggregation_area["name"]
                aggr_names.append(name)
            infometrics_cfg["aggregateBy"] = aggr_names
            if Path(
                self.input.spatial_joins_cfg.parent / "exposure" / "roads.gpkg"
            ).exists():
                infometrics_cfg = add_road_infometrics(infometrics_cfg)
            with open(
                Path(self.input.fiat_output_csv.parent / "infometrics_config.toml"), "w"
            ) as f:
                toml.dump(infometrics_cfg, f)

            metrics_writer = MetricsFileWriter(
                Path(self.input.fiat_output_csv.parent / "infometrics_config.toml")
            )

        # Write non-aggregated metrics
        metrics_full_path = metrics_writer.parse_metrics_to_file(
            df_results=pd.read_csv(self.input.fiat_output_csv),
            metrics_path=self.output.fiat_infometrics,
            write_aggregate=None,
        )

        # Write aggregated metrics
        metrics_writer.parse_metrics_to_file(
            df_results=pd.read_csv(self.input.fiat_output_csv),
            metrics_path=self.output.fiat_infometrics,
            write_aggregate="all",
        )
        aggregation_areas = get_aggregation_areas(self.input.spatial_joins_cfg)

        # Create output map and figure
        create_output_map(
            aggregation_areas,
            self.input.spatial_joins_cfg,
            self.params.scenario_name,
            self.output.fiat_infometrics,
            self.input.fiat_output_csv,
        )

        # Write the infographic
        InforgraphicFactory.create_infographic_file_writer(
            infographic_mode=mode,
            scenario_name=self.params.scenario_name,
            metrics_full_path=metrics_full_path,
            config_base_path=Path(self.input.fiat_output_csv.parent),
            output_base_path=Path(self.output.fiat_infographics.parent),
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
    spatial_joins_cfg: Path,
    event_name: str,
    infometrics_output: Path,
    fiat_output: Path,
):
    """Create vector and image output of the damages per single event or return period.

    Parameters
    ----------
    aggregation_areas: list
        List of aggregation areas to be visualized.
    spatial_joins_cfg: Path
        Path to the spatial joins configuration.
    event_name: str
        Name of the event.
    infometrics_output: Path
        Path to the FIAT infometrics output folder.
    fiat_output: Path
        Path to the FIAT output folder.

    Returns
    -------
    GeoPandas.DataFrame
        An aggregated FIAT results dataframe with damages.

    str
        Path to the PNG file containing a map of the aggregated damages.
    """
    # Create aggregated output
    fn_aggregated_metrics = infometrics_output.parent
    for aggregation_area in aggregation_areas:
        name = aggregation_area["name"]
        fn = aggregation_area["file"]
        field_name = aggregation_area["field_name"]
        gdf_aggregation = gpd.read_file(Path(spatial_joins_cfg.parent / fn))
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
            Path(fn_aggregated_metrics / f"{name}_total_damages_{event_name}.geojson")
        )

        create_total_damage_figure(
            region=Path(spatial_joins_cfg.parent / "geoms" / "region.geojson"),
            gpd_aggregated_damages=gdf_new_aggr,
            output_path=Path(
                fn_aggregated_metrics / f"{name}_total_damages_{event_name}"
            ),
        )
    # Create roads output
    if Path(spatial_joins_cfg.parent / "exposure" / "roads.gpkg").exists():
        gdf_roads = gpd.read_file(
            Path(spatial_joins_cfg.parent / "exposure" / "roads.gpkg")
        )
        exposure_csv = pd.read_csv(Path(fiat_output.parent / "output.csv"))
        inun_depth_roads = exposure_csv.filter(regex="inun_depth").columns
        road_id = exposure_csv[["object_id", "segment_length"]].columns
        exposure_roads = list(inun_depth_roads) + list(road_id)
        roads = exposure_csv[exposure_roads]
        gdf_roads_output = gdf_roads.merge(roads, how="left", on="object_id")
        gdf_roads_output.to_file(
            Path(fn_aggregated_metrics / f"Impact_roads_{event_name}.geojson")
        )


def get_aggregation_areas(spatial_joins_cfg):
    """Get the aggregation areas of the FIAT model.

    Parameters
    ----------
    spatial_joins_cfg: Path
        Path to the spatial joins configuration.

    Returns
    -------
    List
        A list of the aggregation areas.
    """
    spatial_joins = toml.load(spatial_joins_cfg)
    aggregation_areas = spatial_joins["aggregation_areas"]
    return aggregation_areas


def write_risk_infometrics_config(
    rp: list, fiat_model: Path, output_folder: Path, infographics_template: Path
):
    """
    Write risk infometrics configuration file.

    Parameters
    ----------
    rp: list
        A list of the return periods.
    fiat_model : str
        Path to the FIAT model folder.
    output_folder : str
        Path to the metrics output.

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
    "infometrics_config_risk.toml".
    """
    # Get aggregation area
    spatial_joins = toml.load(Path(fiat_model / "spatial_joins.toml"))
    aggregation = spatial_joins["aggregation_areas"][0]["name"]
    x = 0
    rp = [int(i) for i in rp]
    # add mandatory metrics
    mandatory_metrics = {
        "aggregateBy": [aggregation],
        "flood_exceedance": {"column": "inun_depth", "threshold": 0.5, "period": 30},
        "queries": [
            {
                "name": "ExpectedAnnualDamages",
                "description": "Expected annual damages",
                "select": "SUM(`ead_damage`)",
                "filter": "",
                "long_name": "Expected Annual Damages",
                "show_in_metrics_table": "True",
            },
            {
                "name": "FloodedHomes",
                "description": "Homes likely to flood (inun_depth > 0.5) in 30 year period",
                "select": "COUNT(*)",
                "filter": "`Exceedance Probability` > 50 AND `primary_object_type` IN ('residential')",
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
            "select": "COUNT(*)",
            "filter": f"`inun_depth_{rp[x]}.0y` >= 0.5 AND `primary_object_type` = 'residential'",
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
            "filter": f"`inun_depth_{rp[x]}.0y` >= 0.5 AND `primary_object_type` = 'commercial'",
            "long_name": f"Flooded  businesses (RP {rp[x]})",
            "show_in_metrics_table": "True",
        }
        mandatory_metrics["queries"].append(config)
        x += 1

    x = 0
    while x < len(rp):
        config = {
            "name": f"FloodedIndustry{rp[x]}Y",
            "description": f"Number of flooded industrial buildings with return period of {rp[x]} years",
            "select": "COUNT(*)",
            "filter": f"`inun_depth_{rp[x]}.0y` >= 0.5 AND `primary_object_type` = 'industrial'",
            "long_name": f"Flooded  industry (RP {rp[x]})",
            "show_in_metrics_table": "True",
        }
        mandatory_metrics["queries"].append(config)
        x += 1

    # Write risk config file
    config_risk_fn = Path(output_folder / "infometrics_config_risk.toml")

    with open(config_risk_fn, "w") as f:
        toml.dump(mandatory_metrics, f)

    # Write config risk chart
    with open(infographics_template, "r") as toml_file:
        infographic_charts = toml.load(toml_file)

    infographic_charts_dict = {
        "Categories": infographic_charts["Categories"],
        "Other": infographic_charts["Other"],
        "Charts": {},
        "Slices": {},
    }

    x = 0
    while x < len(rp):
        slices_rp_home = {
            "Name": f"{rp[x]}Y Homes",
            "Query": f"FloodedHomes{rp[x]}Y",
            "Chart": f"{rp[x]}Y",
            "Category": "Residential",
        }
        infographic_charts_dict["Slices"][f"Homes_{rp[x]}Y"] = slices_rp_home

        slices_rp_commercial = {
            "Name": f"{rp[x]}Y Homes",
            "Query": f"FloodedHomes{rp[x]}Y",
            "Chart": f"{rp[x]}Y",
            "Category": "Commercial",
        }
        infographic_charts_dict["Slices"][f"Commercial_{rp[x]}Y"] = slices_rp_commercial

        slices_rp_industrial = {
            "Name": f"{rp[x]}Y Homes",
            "Query": f"FloodedHomes{rp[x]}Y",
            "Chart": f"{rp[x]}Y",
            "Category": "Industrial",
        }
        infographic_charts_dict["Slices"][f"Industrial_{rp[x]}Y"] = slices_rp_industrial

        config_chart_rp = {
            "Name": f"{rp[x]}Y",
            "Image": "https://openclipart.org/image/800px/217511",
        }
        infographic_charts_dict["Charts"][f"{rp[x]}Y"] = config_chart_rp
        x += 1

    config_risk_charts_fn = Path(output_folder / "config_risk_charts.toml")

    with open(config_risk_charts_fn, "w") as f:
        toml.dump(infographic_charts_dict, f)

    return config_risk_fn, config_risk_charts_fn.parent


def add_road_infometrics(config_metrics: dict) -> dict:
    """
    Write road infometrics configuration file.

    Parameters
    ----------
    config_metrics : dict
        a dictionary of the metrics.

    Returns
    -------
    config_metrics : dict
        A dictionary of the updated metrics config.
    """
    minor_roads = {
        "name": "MinorFloodedRoads",
        "description": "Roads disrupted for cars",
        "select": "SUM(`segment_length`)",
        "filter": "`inun_depth` <= 0.5",
        "long_name": "Minor flooded roads",
        "show_in_metrics_table": "False",
    }
    major_roads = {
        "name": "MajorFloodedRoads",
        "description": "Roads disrupted for trucks",
        "select": "SUM(`segment_length`)",
        "filter": "`inun_depth` >= 0.5",
        "long_name": "Major flooded roads",
        "show_in_metrics_table": "False",
    }
    config_metrics["queries"].append(minor_roads)
    config_metrics["queries"].append(major_roads)

    return config_metrics


def create_total_damage_figure(
    region: Path, gpd_aggregated_damages: gpd.GeoDataFrame, output_path: Path
):
    """
    Create a total damage figure for the aggregated FIAT results dataframe.

    Parameters
    ----------
    region : Path
        The file path to the region file.
    gpd_aggregated_damages : gpd.GeoDataFrame
        The GeoDataFrame of the aggregated damages.
    output_path : Path
        The file path to store the output file.
    """
    try:
        import contextily as ctx
    except ImportError:
        pass

    web_crs = "EPSG:3857"
    gpd_aggregated_damages = gpd_aggregated_damages.to_crs(web_crs)
    crs = ccrs.epsg(gpd_aggregated_damages.crs.to_epsg())
    region_gdf = gpd.read_file(region)
    region_gdf = region_gdf.to_crs(crs)
    bounds = gpd_aggregated_damages.total_bounds
    buffer = 2000
    bounds = np.array(bounds) + np.array([-buffer, -buffer, buffer, buffer])
    extent = np.array(bounds)[[0, 2, 1, 3]]
    damages_rp = [
        col
        for col in gpd_aggregated_damages.columns
        if col not in ["geometry", "default_aggregation"]
    ]

    for column in damages_rp:
        fig = plt.figure(figsize=(12, 7))
        ax = plt.subplot(projection=crs)
        ax.set_extent(extent, crs=crs)
        ax.set_title(column, size=14)

        #  Basemap
        ctx.add_basemap(ax, crs=crs)

        # Plot data
        gpd_aggregated_damages.plot(
            column=column,
            cmap="Reds",
            scheme="quantiles",
            k=5,
            legend=True,
            legend_kwds={"loc": "lower left"},
            edgecolor="black",  # Add black lines for the grid
            linewidth=0.5,
            ax=ax,
        )

        sm = plt.cm.ScalarMappable(
            cmap="Reds",
            norm=plt.Normalize(
                vmin=gpd_aggregated_damages[column].min(),
                vmax=gpd_aggregated_damages[column].max(),
            ),
        )
        cbar = fig.colorbar(sm, ax=ax, shrink=0.75, orientation="vertical")
        cbar.set_label(f"{column} [$]")

        # Add a region plot in case there is one
        region_gdf.plot(
            ax=ax,
            color="grey",
            edgecolor="black",
            linewidth=2,
            alpha=0.3,
            label="Region",
        )
        fig.savefig(f"{output_path}_{column}", dpi=150, bbox_inches="tight")
