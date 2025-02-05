"""Clip exposure datasets to the region of interest."""
# %% imports
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Root to the input data
root = Path(R"p:\11209169-003-up2030\cases\rio\data\local-data")
# Output root relative to this script
out_root = Path(os.path.abspath(__file__)).parent.parent / "data" / "preprocessed-data"

if not os.path.exists(out_root):
    os.makedirs(out_root)

# Path to the area of interest
region_path = Path(R"p:\11209169-003-up2030\cases\rio\data\region.gpkg")
region = gpd.read_file(region_path)


# %% load and clip data
#  neighborhoods
sectors_path = Path(root, "admin/Setores_CensitA1rios_2010.gpkg")
sectors_gdf = gpd.read_file(sectors_path, mask=region).to_crs("EPSG:31983")
sectors_gdf = sectors_gdf.set_index("id")

# %% census data
census_csv_path = Path(root, "census/Basico_RJ.csv")
census_df = pd.read_csv(census_csv_path, sep=";", encoding="ISO-8859-1", index_col=0)
census_df.index = census_df.index.astype(str)

# %% merge census data with sectors (neighborhoods)
sectors_merged = pd.merge(
    sectors_gdf, census_df.reindex(sectors_gdf.index), left_index=True, right_index=True
)
sectors_merged_gdf = (
    gpd.GeoDataFrame(sectors_merged).set_geometry("geometry").set_crs(sectors_gdf.crs)
)
sectors_merged_gdf.to_file(out_root / "census2010.gpkg", driver="GPKG")

# %% buildings footprints
buildings_path = Path(root, "census/buildings_restored_image_2013.gpkg")
buildings_gdf = gpd.read_file(buildings_path, mask=sectors_gdf)
buildings_gdf.to_file(out_root / "building_footprints.gpkg", driver="GPKG")
# %% replace building footprint with its centroid
buildings_gdf["geometry"] = buildings_gdf.centroid
buildings_gdf.to_file(out_root / "building_centroids.gpkg", driver="GPKG")

# %% building doors (entrances)
entrances_path = Path(root, "census/numero_porta.gpkg")
entrances_gdf = gpd.read_file(entrances_path, mask=sectors_gdf)
entrances_gdf.to_file(out_root / "entrances.gpkg", driver="GPKG")
