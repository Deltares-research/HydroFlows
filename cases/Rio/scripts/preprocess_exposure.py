"""Preprocess clipped exposure datasets.

This scrip combines
- topology data at the entrance level with building footprints
- population data at the sector (neighbourhood) level with building footprints
"""
# %% imports
from pathlib import Path

import geopandas as gpd
import pandas as pd

root = Path(R"p:\11209169-003-up2030\cases\Rio\preprocessed_data")

crs = "EPSG:31983"

# area of interest
region_path = Path(R"p:\11209169-003-up2030\cases\Rio\setup_data\region.gpkg")
region = gpd.read_file(region_path).to_crs(crs)

# %% load clipped data
census_path = root / "census2010.gpkg"
census_gdf = gpd.read_file(census_path).to_crs(crs)

buildings_path = root / "building_footprints.gpkg"
buildings_gdf = gpd.read_file(buildings_path).to_crs(crs)
buildings_gdf.columns = buildings_gdf.columns.str.lower()

entrances_path = root / "entrances.gpkg"
entrances_gdf = gpd.read_file(entrances_path).to_crs(crs)

# %% prep building data

# NOTE that not all buildings have entrances, these are likely unplanned residential buildings

# link buildings entrances to footprints based on cod_lote
buildings_merged_gdf = pd.merge(
    buildings_gdf, entrances_gdf.drop(columns=["geometry"]), on="cod_lote"
)
buildings_merged_gdf = gpd.GeoDataFrame(
    buildings_merged_gdf, geometry="geometry"
).set_crs(buildings_gdf.crs)
# fill typology with residential if missing
residential_code = 2
buildings_merged_gdf["cod_uso"] = (
    buildings_merged_gdf["cod_uso"].fillna(residential_code).astype("int16")
)

# TODO map topologies to curves
# TODO check threshold elevation or sample from DEM

# %% prep population data

buildings_merged_gdf = gpd.sjoin(
    buildings_merged_gdf, census_gdf, how="left", predicate="within"
)

res_buildings = buildings_merged_gdf["cod_uso"] == 2
# per cod_setor total area of building footprints
building_area_per_sector = (
    buildings_merged_gdf.loc[res_buildings, ["cod_setor", "shape__area"]]
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
buildings_merged_gdf["residents"] = 0.0
buildings_merged_gdf.loc[res_buildings, "residents"] = (
    buildings_merged_gdf["cod_setor"].map(residents_per_area)
    * buildings_merged_gdf["shape__area"]
)


# %% save data

keep_columns = {
    "cod_setor": "sector_id",
    "cod_lote": "building_id",
    "cod_uso": "building_use",
    "residents": "residents",
    "altura": "altura",
    "shape__area": "building_area",
    "geometry": "geometry",
}
building_centroids_gdf = buildings_merged_gdf.assign(
    geometry=buildings_merged_gdf.centroid
).set_crs(crs)

building_centroids_gdf[keep_columns.keys()].to_file(
    root / "buildings_centroids_preprocessed.gpkg", driver="GPKG"
)
# %%
