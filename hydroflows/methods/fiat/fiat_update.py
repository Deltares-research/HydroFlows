"""Method for updating a FIAT model with hazard maps."""

from pathlib import Path
from typing import List, Literal, Optional, Union

from hydromt_fiat.fiat import FiatModel

from hydroflows._typing import FileDirPath, ListOfPath, OutputDirPath, WildcardPath
from hydroflows.events import EventSet
from hydroflows.methods.fiat.fiat_utils import copy_fiat_model
from hydroflows.utils.path_utils import make_relative_paths
from hydroflows.workflow.method import ReduceMethod
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["FIATUpdateHazard", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`FIATUpdateHazard` method."""

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file."""

    hazard_maps: Union[WildcardPath, ListOfPath]
    """List of paths to hazard maps the event description file."""

    event_set_yaml: Optional[Path] = None
    """The path to the event description file,
    used to get the return periods of events :py:class:`hydroflows.events.EventSet`.
    Optional for a single hazard map.
    """


class Output(Parameters):
    """Output parameters for :py:class:`FIATUpdateHazard` method."""

    fiat_hazard: Path
    """"The path to the generated combined hazard file (NetCDF) containing all rps."""

    fiat_out_cfg: FileDirPath
    """The path to the newly created settings file."""


class Params(Parameters):
    """Parameters for the :py:class:`FIATUpdateHazard` method.

    See Also
    --------
    :py:class:`hydromt_fiat.fiat.FiatModel`
        For more details on the setup_hazard method used in hydromt_fiat
    """

    output_dir: OutputDirPath
    """Output location relative to the workflow root. The updated model will be stored in <output_dir>/<sim_name>."""

    copy_model: bool = False
    """Create full copy of model or create rel paths in model config."""

    map_type: Literal["water_level", "water_depth"] = "water_level"
    """"The data type of each map specified in the data catalog. A single map type
    applies for all the elements."""

    risk: bool = True
    """"The parameter that defines if a risk analysis is required."""


class FIATUpdateHazard(ReduceMethod):
    """Method for updating a FIAT model with hazard maps.

    Either hazard_maps or single_hazard_map should be provided.
    If single_hazard_map is provided, risk analysis is disabled.

    FIAT simulations are stored in {output_dir}/{sim_name}.

    Parameters
    ----------
    fiat_cfg : Path
        The file path to the FIAT configuration (toml) file.
    event_set_yaml : Path
        The path to the event description file.
    output_dir : str
        Output location of updated model
    hazard_maps : Path or List[Path], optional
        The path to the hazard maps. It can be a list of paths, a single path containing a wildcard,
        or a single path to a single hazard map.
    map_type : Literal["water_level", "water_depth"], optional
        The hazard data type
    sim_name : str, optional
        The name of the simulation folder. If None, the stem of the event set file or the first hazard map is used.

    **params
        Additional parameters to pass to the FIATUpdateHazard instance.
        See :py:class:`fiat_update_hazard Params <hydroflows.methods.fiat.fiat_update_hazard.Params>`.

    See Also
    --------
    :py:class:`fiat_update_hazard Input <hydroflows.methods.fiat.fiat_update_hazard.Input>`
    :py:class:`fiat_update_hazard Output <hydroflows.methods.fiat.fiat_update_hazard.Output>`
    :py:class:`fiat_update_hazard Params <hydroflows.methods.fiat.fiat_update_hazard.Params>`

    """

    name: str = "fiat_update_hazard"

    _test_kwargs = {
        "fiat_cfg": Path("fiat.toml"),
        "event_set_yaml": Path("event_set.yaml"),
        "hazard_maps": Path("hazard_{event}.nc"),
        "output_dir": "simulations",
    }

    def __init__(
        self,
        fiat_cfg: Path,
        event_set_yaml: Path,
        hazard_maps: Union[Path, List[Path]],
        output_dir: str,
        risk: bool = True,
        map_type: Literal["water_level", "water_depth"] = "water_level",
        **params,
    ):
        self.input: Input = Input(
            fiat_cfg=fiat_cfg,
            event_set_yaml=event_set_yaml,
            hazard_maps=hazard_maps,
        )

        # check if risk analysis is required
        if (
            isinstance(self.input.hazard_maps, list)
            and len(self.input.hazard_maps) == 1
        ):
            risk = False

        self.params: Params = Params(
            output_dir=output_dir,
            map_type=map_type,
            risk=risk,
            **params,
        )
        if self.params.risk and self.input.event_set_yaml is None:
            raise ValueError(
                "Event set is required for risk analysis. "
                "Please provide an event set yaml file or set risk=False."
            )

        # output root is the simulation folder
        fiat_root = self.params.output_dir

        if not self.params.copy_model and not self.params.output_dir.is_relative_to(
            self.input.fiat_cfg.parent
        ):
            raise ValueError(
                "Output directory must be relative to input directory when not copying model."
            )

        self.output: Output = Output(
            fiat_hazard=fiat_root / "hazard" / "hazard.nc",
            fiat_out_cfg=fiat_root / "settings.toml",
        )

    def _run(self):
        """Run the FIATUpdateHazard method."""
        # make sure hazard maps is a list
        hazard_maps = self.input.hazard_maps
        if not isinstance(hazard_maps, list):
            hazard_maps = [hazard_maps]

        # Load the existing
        root = self.input.fiat_cfg.parent
        out_root = self.output.fiat_out_cfg.parent

        if self.params.copy_model:
            copy_fiat_model(root, out_root)

        model = FiatModel(
            root=root,
            mode="r",
        )
        model.read()

        # Make all paths relative in the config
        if not self.params.copy_model:
            config = {
                k: make_relative_paths(model.config[k], root, out_root)
                for k in model.config
            }
            config["exposure"]["csv"] = make_relative_paths(
                model.config["exposure"]["csv"], root, out_root
            )
            config["exposure"]["geom"] = make_relative_paths(
                model.config["exposure"]["geom"], root, out_root
            )
        else:
            config = model.config

        # READ the hazard catalog
        if self.input.event_set_yaml is not None:
            event_set: EventSet = EventSet.from_yaml(self.input.event_set_yaml)
            # filter out the right path names / sort them in the right order
            names = [event["name"] for event in event_set.events]
            hazard_fns = []
            for name in names:
                for fn in hazard_maps:
                    if name in fn.as_posix():
                        hazard_fns.append(fn)
                        break
            if len(hazard_fns) != len(names):
                raise ValueError(
                    f"Could not find all hazard maps for the event set {self.input.event_set_yaml}"
                )
            hazard_maps = hazard_fns

        # get return periods
        if self.params.risk:  # get matching hazard maps and return periods
            rps = [event_set.get_event(name).return_period for name in names]
        else:
            rps = None

        # Setup the hazard map
        # TODO: for some reason hydromt_fiat removes any existing nodata values from flood maps and then later returns
        # a ValueError if the metadata of those same maps does not contain a nodata value. Here we impose a random -9999.
        model.setup_config(**config)
        model.setup_hazard(
            map_fn=hazard_maps,
            map_type=self.params.map_type,
            rp=rps,
            risk_output=self.params.risk,
            var=self.params.map_type,  # water_level or water_depth
            nodata=-9999.0,
        )
        # change root to simulation folder
        model.set_root(out_root, mode="w+")
        hazard_out = self.output.fiat_hazard.relative_to(
            self.output.fiat_out_cfg.parent
        ).as_posix()
        if self.params.risk:
            model.write_grid(hazard_out)
            model.set_config("hazard.settings.var_as_band", True)
        else:
            model.write_maps(hazard_out)
        model.set_config("hazard.file", hazard_out)

        # Write the config
        model.write_config()

        # remove empty directories using pathlib in out_root
        for d in out_root.iterdir():
            if d.is_dir() and not list(d.iterdir()):
                d.rmdir()
