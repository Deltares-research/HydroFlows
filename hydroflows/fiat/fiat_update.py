"""Method for updating a FIAT model with hazard maps."""

import logging
from pathlib import Path
from typing import List, Literal, Optional, Union

from hydromt import log
from hydromt_fiat import FIATModel
from workflowpy._typing import FileDirPath, ListOfPath, OutputDirPath, WildcardPath
from workflowpy.method import ReduceMethod
from workflowpy.parameters import Parameters

from hydroflows.events import EventSet

__all__ = ["FIATUpdateHazard", "Input", "Output", "Params"]


class Input(Parameters):
    """Input parameters for the :py:class:`FIATUpdateHazard` method."""

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file."""

    hazard_maps: Union[WildcardPath, ListOfPath]
    """List of paths to hazard maps the event description file."""

    event_set_yaml: Optional[FileDirPath] = None
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

    hazard_type: Literal["water_level", "water_depth"] = "water_level"
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
    hazard_type : Literal["water_level", "water_depth"], optional
        The hazard data type
    sim_name : str, optional
        The name of the simulation folder. If None, the stem of the event set file or the first hazard map is used.

    **params
        Additional parameters to pass to the FIATUpdateHazard instance.
        See :py:class:`fiat_update_hazard Params <hydroflows.fiat.fiat_update_hazard.Params>`.

    See Also
    --------
    :py:class:`fiat_update_hazard Input <hydroflows.fiat.fiat_update_hazard.Input>`
    :py:class:`fiat_update_hazard Output <hydroflows.fiat.fiat_update_hazard.Output>`
    :py:class:`fiat_update_hazard Params <hydroflows.fiat.fiat_update_hazard.Params>`

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
        hazard_type: Literal["water_level", "water_depth"] = "water_level",
        **params,
    ):
        self.input: Input = Input(
            fiat_cfg=fiat_cfg,
            event_set_yaml=event_set_yaml,
            hazard_maps=hazard_maps,
        )

        self.params: Params = Params(
            output_dir=output_dir,
            hazard_type=hazard_type,
            risk=risk,
            **params,
        )

        if self.params.risk and self.input.event_set_yaml is None:
            raise ValueError(
                "Event set is required for risk analysis. "
                "Please provide an event set yaml file or set risk=False."
            )

        if not self.params.copy_model and not self.params.output_dir.is_relative_to(
            self.input.fiat_cfg.parent
        ):
            raise ValueError(
                "Output directory must be relative to input directory when not copying model."
            )

        self.output: Output = Output(
            fiat_hazard=self.params.output_dir / "hazard.nc",
            fiat_out_cfg=self.params.output_dir / "settings.toml",
        )

    def _run(self):
        """Run the FIATUpdateHazard method."""
        log.initialize_logging(
            file_path=Path(self.input.fiat_cfg.parent, "hydromt.log"),
            level=logging.INFO,
        )
        # Open the existing model
        model = FIATModel(
            root=self.input.fiat_cfg.parent,
            mode="r+",
            config_fname=self.input.fiat_cfg.name,
        )

        # Move it
        model.move(
            root=self.output.fiat_out_cfg.parent,
            write=self.params.copy_model,
        )

        hazard_fnames = self.input.hazard_maps
        return_periods = None
        # Check for the event set
        if self.input.event_set_yaml is not None:
            event_set = EventSet.from_yaml(self.input.event_set_yaml)
            event_ids = [event["name"] for event in event_set.events]
            files = map(
                lambda x: next(
                    (item for item in hazard_fnames if x in item.as_posix()), None
                ),
                event_ids,
            )
            files = list(files)
            if not all(files):
                raise ValueError(
                    f"Could not find all hazard maps for \
the event set {self.input.event_set_yaml}"
                )
            hazard_fnames = files

            # Get the return periods if applicable
            if self.params.risk:
                return_periods = [
                    event_set.get_event(name).return_period for name in event_ids
                ]

        # Setup the hazard
        model.hazard.create(
            hazard_fnames=hazard_fnames,
            return_periods=return_periods,
            risk=self.params.risk,
            region=(model.region is not None),
        )

        # Write the data back
        model.hazard.write()
        model.config.write()
