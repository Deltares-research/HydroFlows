"""FIAT updating submodule/ rules."""
from pathlib import Path

import geopandas as gpd
from hydromt import open_raster
from hydromt_fiat.fiat import FiatModel
from pydantic import BaseModel, FilePath
from shapely import box

from ..method import Method


class Input(BaseModel):
    """Input FIAT update params."""

    hazard_map: FilePath
    fiat_cfg: FilePath


class Params(BaseModel):
    """FIAT update params."""

    map_type: str = "water_depth"
    var: str = "zsmax"


class Output(BaseModel):
    """Output FIAT build params."""

    fiat_haz: Path


class FIATUpdateHazard(Method):
    """Method for updating a FIAT model with hazard maps."""

    name: str = "fiat_update_hazard"
    params: Params = Params()
    input: Input
    output: Output

    def run(self):
        """Run the FIAT update hazard rule."""
        # Load the existing
        root = self.input.fiat_cfg.parent
        model = FiatModel(
            root=root,
            mode="w+",
        )
        model.read()

        ## WARNING! code below is necessary for now, as hydromt_fiat cant deliver
        # Read the hazard file
        da = open_raster(self.input.hazard_map)
        # Setup a region
        region = gpd.GeoDataFrame(
            geometry=[box(*model.exposure.bounding_box())],
        )
        region = region.set_crs(model.exposure.crs)
        # Clip the hazard data with a small buffer
        da = da.raster.clip_geom(
            region.to_crs(da.raster.crs),
            buffer=2,
        )

        # Setup the hazard map
        model.setup_hazard(
            da,
            map_type=self.params.map_type,
            var=self.params.var,
        )

        ## Warning!! code below is again necessary
        model.maps["hazard_map"] = model.maps["hazard_map"].assign_attrs(
            {"_FillValue": da._FillValue}
        )
        model.maps["hazard_map"] = model.maps["hazard_map"].raster.gdal_compliant()
        # Write the maps
        model.write_maps(fn=Path("hazard", "hazard_map.nc").as_posix())

        # Adjust the config for now (waiting for hydromt_fiat)
        del model.config["hazard"]["settings"]
        del model.config["hazard"]["return_periods"]
        # Write the config
        model.write_config()
