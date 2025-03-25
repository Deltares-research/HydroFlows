"""Preprocess clipped exposure datasets.

This scrip combines
- topology data at the entrance level with building footprints
- population data at the sector (neighbourhood) level with building footprints
"""
# %% imports
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml
from shapely.geometry import MultiPolygon, Polygon

data_source = (
    Path(os.path.abspath(__file__)).parent.parent / "data" / "preprocessed-data"
)  # make a relative path

crs = "EPSG:31983"

# area of interest
region_path = Path(data_source.parent) / "region.geojson"
region = gpd.read_file(region_path).to_crs(crs)


# The building footprints are saved in 3D, but we need to convert them to 2D
def convert_to_2d(geometry):
    """Convert 3D geometry to 2D."""
    if geometry.geom_type == "Polygon":
        # Convert Polygon Z to 2D
        return Polygon([(x, y) for x, y, z in geometry.exterior.coords])
    elif geometry.geom_type == "MultiPolygon":
        # Convert MultiPolygon Z to 2D
        return MultiPolygon(
            [
                Polygon([(x, y) for x, y, z in poly.exterior.coords])
                for poly in geometry.geoms
            ]
        )  # Use geometry.geoms here
    else:
        return geometry


def map_social_class(income):
    """Map the social class to the income."""
    if income < 2403.04:
        return "DE"
    elif income > 2403.04 and income < 3980.38:
        return "C2"
    elif income > 3980.38 and income < 7017.64:
        return "C1"
    elif income > 7017.64 and income < 12683.34:
        return "B2"
    elif income > 12683.34 and income < 26811.68:
        return "B1"
    elif income > 26811.68:
        return "A"
    else:
        return ""


# %% load clipped data
census_path = data_source / "census2010.gpkg"
census_gdf = gpd.read_file(census_path).to_crs(crs)

buildings_path = data_source / "building_footprints.gpkg"
buildings_gdf = gpd.read_file(buildings_path).to_crs(crs)
buildings_gdf.columns = buildings_gdf.columns.str.lower()

entrances_path = data_source / "entrances.gpkg"
entrances_gdf = gpd.read_file(entrances_path).to_crs(crs)

# %% load csv data
social_class_path = (
    Path(data_source.parent)
    / "local-data"
    / "census"
    / "damages"
    / "social_class_building_type_mapping.csv"
)
social_class = pd.read_csv(social_class_path)

# %% prep building data

# NOTE that not all buildings have entrances, these are likely unplanned residential buildings

# %% Create 2D building footprints
# Apply the conversion to each geometry in the GeoDataFrame
buildings_gdf["geometry"] = buildings_gdf["geometry"].apply(convert_to_2d)
buildings_gdf = buildings_gdf.dissolve(by="cod_lote")
buildings_gdf = buildings_gdf.explode()
del buildings_gdf["clnp"]
# %% link buildings entrances to footprints based on cod_lote
# NOTE There are duplicates in the cod_lote so merge might create weird duplicates, prefer spatialjoint
buildings_gdf.to_crs(entrances_gdf.crs, inplace=True)
occupancy_gdf = gpd.sjoin_nearest(buildings_gdf, entrances_gdf)
occupancy_gdf = occupancy_gdf[["geometry", "cod_uso", "altura", "shape__area"]]
occupancy_gdf.drop_duplicates(
    subset="geometry", inplace=True
)  # NOTE currently no logic behind dropping. Could drop the higher impacts. Discuss with partners

# Set crs
if buildings_gdf.crs != occupancy_gdf.crs:
    occupancy_gdf = gpd.GeoDataFrame(occupancy_gdf, geometry="geometry").set_crs(
        buildings_gdf.crs
    )

# fill typology with residential if missing
dic_occupancy = {
    1: "Commercial and Service",
    2: "Residential",
    3: "Commercial and Service",
    4: "Commercial and Service",
    5: "Industrial",
    6: "Commercial and Service",
    7: "Residential",
    8: "Residential",
    9: "Residential",
}
occupancy_gdf["primary_object_type"] = (
    occupancy_gdf["cod_uso"].map(dic_occupancy).fillna("Residential")
)
del occupancy_gdf["cod_uso"]

# JRC Curve Mapping
# Translate occupancy to JRC Damage Curves  #TODO Decide on occupancy translation
dic_occupancy_to_jrc_damages = {
    "Commercial and Service": "commercial",
    "Residential": "residential",
    "Temples, Churches, etc.": "commercial",
    "Mixed (commercial and residential)": "commercial",
    "Industrial": "industrial",
    "Public": "commercial",
    "Empty Land": "residential",
    "Abandoned": "residential",
    "Others": "residential",
}
occupancy_gdf_jrc = occupancy_gdf.copy()
occupancy_gdf_jrc["primary_object_type"] = (
    occupancy_gdf["primary_object_type"]
    .map(dic_occupancy_to_jrc_damages)
    .fillna("residential")
)

# TODO check threshold elevation or sample from DEM


# %% prep population data

occupancy_gdf = gpd.sjoin(occupancy_gdf_jrc, census_gdf, how="left", predicate="within")

res_buildings = occupancy_gdf["primary_object_type"] == "residential"

# per cod_setor total area of building footprints
building_area_per_sector = (
    occupancy_gdf.loc[res_buildings, ["cod_setor", "shape__area"]]
    .groupby("cod_setor")
    .sum()["shape__area"]
)
# average residents per sector (V002) per footprint area
residents_per_sector = (
    census_gdf.set_index("cod_setor")["V002"]
    .astype(float)
    .reindex(building_area_per_sector.index)
)
residents_per_area = residents_per_sector / building_area_per_sector

# get residents (population) per building entrance
mapped_residents = occupancy_gdf["cod_setor"].map(residents_per_area)

# Create a new residents column with conditional assignment
occupancy_gdf["residents"] = np.where(
    res_buildings,  # NOTE takes all as residential classified assets.
    mapped_residents * occupancy_gdf["shape__area"],
    0.0,  # Default value for other rows
)

# %% Map local occupancy types based on income
# Combine income csv with spatial sectors
occupancy_gdf["V005"] = occupancy_gdf["V005"].apply(
    lambda x: np.nan if x is None else x
)
occupancy_gdf["V005"] = occupancy_gdf["V005"] = occupancy_gdf["V005"].apply(
    lambda x: float(x.replace(",", ".")) if pd.notna(x) else np.nan
)
# either adjust income to inflation or map to 2010 values - not available I think
occupancy_gdf["V005"] = (
    occupancy_gdf["V005"] * 2.75
)  # https://www3.bcb.gov.br/CALCIDADAO/publico/corrigirPorIndice.do?method=corrigirPorIndice

# Map social class
occupancy_bf_residential = occupancy_gdf[
    occupancy_gdf["primary_object_type"] == "residential"
]
occupancy_bf_com_ind = occupancy_gdf[
    occupancy_gdf["primary_object_type"] != "residential"
]

for index, row in occupancy_bf_residential.iterrows():
    if pd.isna(row["V005"]) or row["V005"] is None:
        nearest_idx = occupancy_bf_residential.sindex.nearest(
            row["geometry"], return_all=False
        )
        if isinstance(nearest_idx, (list, np.ndarray)):
            for idx in nearest_idx:
                if pd.notna(occupancy_bf_residential.iloc[idx]["V005"][0]):
                    nearest_idx = idx
                    break
        nearest_row = occupancy_bf_residential.iloc[nearest_idx]
        occupancy_bf_residential.at[index, "V005"] = nearest_row["V005"]

# Apply mapping function
occupancy_bf_residential["social_class"] = occupancy_bf_residential["V005"].apply(
    map_social_class
)
occupancy_bf_com_ind["V005"] = None

new_occupancy = pd.concat(
    [occupancy_bf_residential, occupancy_bf_com_ind], ignore_index=True
)
new_occupancy = new_occupancy.reset_index(drop=True)

# Map building
social_class_dict = dict(
    zip(social_class["SOCIALCLASS"], social_class["BUILDINGSTANDARD"])
)

new_occupancy["secondary_object_type"] = new_occupancy["social_class"].map(
    social_class_dict
)

for index, row in new_occupancy.iterrows():
    if row["primary_object_type"] == "commercial":
        new_occupancy.at[index, "secondary_object_type"] = "commercial"
    elif row["primary_object_type"] == "industrial":
        new_occupancy.at[index, "secondary_object_type"] = "industrial"
# %% save data

# Define file names
fn_building_footprints = "building_footprints_2d.gpkg"
fn_local = "local_occupancy_pre_processed.gpkg"
fn_floor_height = "finished_floor_height.gpkg"
fn_asset_population = "asset_population.gpkg"

# Save bf
buildings_gdf.to_file(data_source / fn_building_footprints)

## Save occupancy
new_occupancy[["geometry", "primary_object_type", "secondary_object_type"]].to_file(
    (data_source / fn_local)
)

# Save Finished Floor Height
##convert from cm into meters
new_occupancy["altura"] = new_occupancy["altura"] / 100
new_occupancy[["altura", "geometry"]].to_file(data_source / fn_floor_height)

## Save population
new_occupancy[["residents", "geometry"]].to_file(
    data_source / fn_asset_population, driver="GPKG"
)


# %%
# Create a dictionary
# Helper function to create entries
def create_entry(path, crs=None, datatype: str = "vector"):
    """Create a dictionary entry representing a GeoDataFrame or a DataFrame."""
    if datatype == "vector":
        return {
            "data_type": "GeoDataFrame",
            "path": path,
            "driver": "vector",
            "filesystem": "local",
            "crs": crs.to_epsg() if crs else None,
        }
    elif datatype == "csv":
        return {
            "data_type": "DataFrame",
            "path": path,
            "driver": "csv",
            "filesystem": "local",
        }


# Dict
yaml_dict = {
    "preprocessed_occupaction": create_entry(
        fn_local,
        occupancy_gdf.crs,
    ),
    "preprocessed_floor_height": create_entry(
        fn_floor_height,
        occupancy_gdf.crs,
    ),
    "preprocessed_asset_population": create_entry(
        fn_asset_population,
        occupancy_gdf.crs,
    ),
}

# Save the YAML catalog
catalog_path = data_source / "data_catalog.yml"
with open(catalog_path, "w") as yaml_file:
    yaml.dump(yaml_dict, yaml_file, default_flow_style=False, sort_keys=False)
# %%
