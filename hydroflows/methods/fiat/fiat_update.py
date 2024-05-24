"""FIAT updating submodule/ rules."""
from pathlib import Path

import yaml
from hydromt_fiat import FiatModel
from pydantic import BaseModel, FilePath

from hydroflows.methods.method import Method


class Input(BaseModel):
    """Input FIAT update params."""

    event_catalog: FilePath
    fiat_cfg: FilePath


class Params(BaseModel):
    """FIAT update params."""

    map_type: str = "water_depth"
    risk: bool = False
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
        # READ the hazard catalog
        hc_path = Path(self.input.event_catalog)
        with open(hc_path, "r") as _r:
            hc = yaml.safe_load(_r)

        paths = [
            Path(
                hc_path.parent, hc["roots"]["root_hazards"], item["hazards"][0]["path"]
            )
            for item in hc["events"]
        ]
        rp = [1 / item["probability"] for item in hc["events"]]

        # Setup the hazard map
        model.setup_hazard(
            paths,
            map_type=self.params.map_type,
            rp=rp,
            risk_output=self.params.risk,
        )

        model.write_grid(fn=Path("hazard", self.output.fiat_haz.name).as_posix())

        model.set_config("hazard.settings.var_as_band", True)

        # Write the config
        model.write_config()
