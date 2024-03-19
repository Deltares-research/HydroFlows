"""Module/ Rule for building FIAT models."""
import os
from pathlib import Path
from typing import List

import hydromt_fiat
from hydromt.config import configread
from hydromt_fiat.fiat import FiatModel
from pydantic import BaseModel, FilePath

from ..method import HYDROMT_CONFIG_DIR, Method

__all__ = ["FIATBuild"]

FIAT_DATA_PATH = Path(
    os.path.dirname(hydromt_fiat.__file__),
    "data",
    "hydromt_fiat_catalog_global.yml",
).as_posix()


class Input(BaseModel):
    """Input FIAT build params."""

    region: FilePath


class Params(BaseModel):
    """FIAT build params."""

    config: Path = Path(HYDROMT_CONFIG_DIR, "fiat_build.yaml")
    data_libs: List[str] = ["artifact_data"]
    continent: str = "South America"

class Output(BaseModel):
    """Output FIAT build params."""

    fiat_cfg: Path


class FIATBuild(Method):
    """Rule for building FIAT."""

    name: str = "fiat_build"
    params: Params = Params()
    input: Input
    output: Output

    def run(self):
        """Run the FIAT build rule."""
        # Read template config
        opt = configread(self.params.config)
        # Add additional information
        region_gdf = gpd.read_file(self.input.region.as_posix()).to_crs(4326)
        opt.update(
            {"setup_region": {
                "region": {"geom": region_gdf}
            }}
        )
        #Setup the model
        root = self.output.fiat_cfg.parent
        model = FiatModel(
            root = root,
            mode="w+",
            data_libs=[FIAT_DATA_PATH] + self.params.data_libs,
        )
        # Build the model
        model.build(opt=opt)


if __name__ == "__main__":
    pass
