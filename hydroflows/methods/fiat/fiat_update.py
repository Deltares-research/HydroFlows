"""FIAT updating submodule/ rules."""
from pathlib import Path

from hydromt_fiat.fiat import FiatModel
from pydantic import BaseModel

from hydroflows.events import EventSet
from hydroflows.methods.method import Method
from hydroflows.utils import make_relative_paths


class Input(BaseModel):
    """Input parameters for the :py:class:`FIATUpdateHazard` method."""

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file."""

    event_set_yaml: Path
    """The path to the event description file,
    see also :py:class:`hydroflows.workflows.events.Event`."""


class Output(BaseModel):
    """Output parameters for :py:class:`FIATUpdateHazard` method."""

    fiat_hazard: Path
    """"The path to the generated combined hazard file (NetCDF) containing all rps."""

    fiat_out_cfg: Path


class Params(BaseModel):
    """Parameters for the :py:class:`FIATUpdateHazard` method.

    See Also
    --------
    :py:class:`hydromt_fiat.fiat.FiatModel`
        For more details on the setup_hazard method used in hydromt_fiat
    """

    map_type: str = "water_depth"
    """"The data type of each map speficied in the data catalog. A single map type
    applies for all the elements."""

    risk: bool = False
    """"The parameter that defines if a risk analysis is required."""

    var: str = "zsmax"
    """"Variable name."""


class FIATUpdateHazard(Method):
    """Rule for updating a FIAT model with hazard maps.

    This class utilizes the :py:class:`Params <hydroflows.methods.fiat.fiat_update.Params>`,
    :py:class:`Input <hydroflows.methods.fiat.fiat_update.Input>`, and
    :py:class:`Output <hydroflows.methods.fiat.fiat_update.Output>` classes to update
    a FIAT model with hazard maps.
    """

    name: str = "fiat_update_hazard"

    def __init__(self, fiat_cfg: Path, event_yaml: Path, **params):
        """Create and validate a FIATUpdateHazard instance.

        FIAT simulations are stored in a simulations/{event_name} subdirectory of the basemodel.

        Parameters
        ----------
        fiat_cfg : Path
            The file path to the FIAT configuration (toml) file.
        event_yaml : Path
            The path to the event description file.
        **params
            Additional parameters to pass to the FIATUpdateHazard instance.
            See :py:class:`fiat_update_hazard Params <hydroflows.methods.fiat.fiat_update_hazard.Params>`.

        See Also
        --------
        :py:class:`fiat_update_hazard Input <hydroflows.methods.fiat.fiat_update_hazard.Input>`
        :py:class:`fiat_update_hazard Output <hydroflows.methods.fiat.fiat_update_hazard.Output>`
        :py:class:`fiat_update_hazard Params <hydroflows.methods.fiat.fiat_update_hazard.Params>`

        """
        self.params: Params = Params(**params)
        self.input: Input = Input(fiat_cfg=fiat_cfg, event_yaml=event_yaml)
        # NOTE: FIAT runs with full event sets with RPs. Name of event set is the stem of the event set file
        event_set_name = self.input.event_set_yaml.stem
        fiat_hazard = (
            self.input.fiat_cfg.parent / "simulations" / event_set_name / "hazard.tif"
        )
        fiat_out_cfg = (
            self.input.fiat_cfg.parent
            / "simulations"
            / event_set_name
            / "settings.toml"
        )
        self.output: Output = Output(fiat_hazard=fiat_hazard, fiat_out_cfg=fiat_out_cfg)

        def run(self):
            """Run the FIATUpdateHazard method."""
            # Load the existing
            root = self.input.fiat_cfg.parent
            out_root = self.output.fiat_out_cfg.parent
            if not out_root.is_relative_to(root):
                raise ValueError("out_root should be a subdirectory of root")

            model = FiatModel(
                root=root,
                mode="w+",
            )
            model.read()

            # Make all paths relative in the config
            config = make_relative_paths(model.config, root, out_root)

            ## WARNING! code below is necessary for now, as hydromt_fiat cant deliver
            # READ the hazard catalog
            event_set_path = Path(self.input.event_set_yaml)
            # with open(event_set_path, "r") as _r:
            #     hc = yaml.safe_load(_r)
            event_set: EventSet = EventSet.from_yaml(self.input.event_set_yaml)
            paths = [
                Path(
                    event_set_path.parent,
                    event_set.roots["root_hazards"],
                    item.hazards[0]["path"],
                )
                for item in event_set.events
            ]
            rps = [1 / item.probability for item in event_set.events]

            # Setup the hazard map
            model.setup_hazard(
                paths,
                map_type=self.params.map_type,
                rp=rps,
                risk_output=self.params.risk,
            )
            # change root to simulation folder
            model.set_root(out_root, mode="w+")
            model.write_grid(fn=fiat_hazard)
            config.update("hazard.settings.var_as_band", True)
            config.update("hazard.settings.path", fiat_hazard)
            # model.set_config("hazard.settings.var_as_band", True)

            # update config
            model.setup_config(**config)
            # Write the config
            model.write_config()
