"""Script to get raster bathymetry for Acari river based on points."""

import geopandas as gpd
import hydromt.raster as hr
import numpy as np
from alphashape import alphashape

# %%
# Code to derive the river shape from points and interpolate heights to raster
# Load the GPKG file
gpkg_path = R"p:\11209169-003-up2030\cases\rio\data\local-data\bathymetry\ACARI_BATHYMETRY_MERGED.gpkg"
gdf = gpd.read_file(gpkg_path)

gdf = gdf[~gdf["geometry"].isna()]

# Extract points
points = np.array([(geom.x, geom.y) for geom in gdf.geometry])

# River polygon using Alpha Shapes
alpha_value = 0.05  # Adjust this value based on how tight the polygon should be
river_polygon = alphashape(points, alpha_value)

# Convert to a GeoDataFrame
river_mask = gpd.GeoDataFrame(geometry=[river_polygon], crs=gdf.crs)

# Save river polygon
# river_mask.to_file(R"p:\11209169-003-up2030\cases\rio\data\local-data\bathymetry\river_polygon_merged.geojson", driver="GeoJSON")

xmin, ymin, xmax, ymax = gdf.total_bounds
res = 1  # m
transform = (res, 0.0, xmin, 0.0, -res, ymax)
shape = (int((ymax - ymin) / res), int((xmax - xmin) / res))
grid = hr.full_from_transform(
    transform=transform,
    shape=shape,
    lazy=True,
    crs=gdf.crs,
)
# interpolate the bathymetry to the raster
da_dtm = grid.raster.rasterize(gdf, col_name="Z", nodata=np.nan)
da_dtm = da_dtm.raster.interpolate_na("cubic")
da_dtm = da_dtm.where(da_dtm.raster.geometry_mask(river_mask))

da_dtm.raster.to_raster(
    R"p:\11209169-003-up2030\cases\rio\data\local-data\bathymetry\ACARI_BATHYMETRY_MERGED.tif"
)
