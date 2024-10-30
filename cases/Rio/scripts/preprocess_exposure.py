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
from shapely.geometry import MultiPolygon, Polygon

data_source = (
    Path(os.path.abspath(__file__)).parent.parent
    / "setup_data"
    / "hydromt_fiat_exposure"
)  # make a relative path

crs = "EPSG:31983"

# area of interest
region_path = Path(data_source) / "region.gpkg"
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


# %% load clipped data
census_path = data_source / "census2010.gpkg"
census_gdf = gpd.read_file(census_path).to_crs(crs)

buildings_path = data_source / "building_footprints.gpkg"
buildings_gdf = gpd.read_file(buildings_path).to_crs(crs)
buildings_gdf.columns = buildings_gdf.columns.str.lower()

entrances_path = data_source / "entrances.gpkg"
entrances_gdf = gpd.read_file(entrances_path).to_crs(crs)

# %% prep building data


# NOTE that not all buildings have entrances, these are likely unplanned residential buildings

# %% Create 2D building footprints
# Apply the conversion to each geometry in the GeoDataFrame
buildings_gdf["geometry"] = buildings_gdf["geometry"].apply(convert_to_2d)

# %% link buildings entrances to footprints based on cod_lote
# NOTE There are duplicates in the cod_lote so merge might create weird duplicates, prefer spatialjoint
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

# TODO: Create strategy to possibly remove duplicate building footprints!

# TODO map topologies to curves - as soon we get the correct curves
# occupancy_gdf.to_file((data_source / "occupancy_pre_processed_translated_occupaction_local.gpkg"))
# ...

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

occupancy_gdf = gpd.sjoin(occupancy_gdf, census_gdf, how="left", predicate="within")

res_buildings = occupancy_gdf["primary_object_type"] == "Residential"

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

# %% save data

# Save bf
buildings_gdf.to_file(data_source / "building_footprints_2d.gpkg")

## Save occupancy
occupancy_gdf[["geometry", "primary_object_type"]].to_file(
    (data_source / "occupancy_pre_processed_translated_occupaction_local_dummy.gpkg")
)
occupancy_gdf_jrc[["geometry", "primary_object_type"]].to_file(
    (data_source / "occupancy_pre_processed_translated_occupaction_jrc.gpkg")
)

# Save Finished Floor Height
##convert from cm into meters
occupancy_gdf["altura"] = occupancy_gdf["altura"] / 100
occupancy_gdf[["altura", "geometry"]].to_file(
    data_source / "finished_floor_height.gpkg"
)

## Save population
occupancy_gdf[["residents", "geometry"]].to_file(
    data_source / "asset_population.gpkg", driver="GPKG"
)
