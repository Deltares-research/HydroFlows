"""Module/ Rule for building FIAT models."""
import sys
from pathlib import Path
from typing import List

from hydromt.config import configread
from hydromt_fiat.fiat import FiatModel
from pydantic import BaseModel, FilePath

from hydroflows.templates import TEMPLATE_DIR

from ..method import Method

__all__ = ["FIATBuild"]
PYTHON_PATH = Path(sys.executable).parent


class Input(BaseModel):
    """Input FIAT build params."""

    region: FilePath


class Params(BaseModel):
    """FIAT build params."""

    config: Path = Path(TEMPLATE_DIR, "fiat_build.yml")
    data_libs: List[str] = [
        "artifact_data",
        Path(
            PYTHON_PATH,
            "Lib",
            "site-packages",
            "hydromt_fiat",
            "data",
            "hydromt_fiat_catalog_global.yml",
        ).as_posix(),
    ]
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
        opt.update(
            {"setup_region": {
                "region": {"geom": self.input.region.as_posix()}
            }}
        )
        #Setup the model
        root = self.output.fiat_cfg.parent
        model = FiatModel(
            root = root,
            mode="w+",
            data_libs=self.params.data_libs,
        )
        # Build the model
        model.build(opt=opt)


if __name__ == "__main__":
    pass
