"""FIAT updating submodule/ rules."""

from pathlib import Path
from typing import List, Union

import geopandas as gpd
from hydromt_fiat.fiat import FiatModel

from hydroflows.events import EventSet
from hydroflows.methods.method import ReduceMethod
from hydroflows.methods.method_parameters import Parameters, ReduceParameters
from hydroflows.utils import make_relative_paths


class Input(ReduceParameters):
    """Input parameters for the :py:class:`FIATUpdateHazard` method."""

    fiat_cfg: Path
    """The file path to the FIAT configuration (toml) file."""

    event_set_yaml: Path
    """The path to the event description file, used to filter hazard maps,
    see also :py:class:`hydroflows.workflows.events.Event`."""

    hazard_maps: List[Path]
    """List of paths to hazard maps the event description file."""


class Output(Parameters):
    """Output parameters for :py:class:`FIATUpdateHazard` method."""

    fiat_hazard: Path
    """"The path to the generated combined hazard file (NetCDF) containing all rps."""

    fiat_out_cfg: Path


class Params(Parameters):
    """Parameters for the :py:class:`FIATUpdateHazard` method.

    See Also
    --------
    :py:class:`hydromt_fiat.fiat.FiatModel`
        For more details on the setup_hazard method used in hydromt_fiat
    """

    map_type: str = "water_depth"
    """"The data type of each map specified in the data catalog. A single map type
    applies for all the elements."""

    risk: bool = True
    """"The parameter that defines if a risk analysis is required."""

    var: str = "zsmax"
    """"Variable name."""


class FIATUpdateHazard(ReduceMethod):
    """Rule for updating a FIAT model with hazard maps.

    This class utilizes the :py:class:`Params <hydroflows.methods.fiat.fiat_update.Params>`,
    :py:class:`Input <hydroflows.methods.fiat.fiat_update.Input>`, and
    :py:class:`Output <hydroflows.methods.fiat.fiat_update.Output>` classes to update
    a FIAT model with hazard maps.
    """

    name: str = "fiat_update_hazard"
    # reduce_refs = {"event": "hazard_maps"}

    def __init__(
        self,
        fiat_cfg: Path,
        event_set_yaml: Path,
        hazard_maps: Union[Path, List[Path]],
        **params,
    ):
        """Create and validate a FIATUpdateHazard instance.

        FIAT simulations are stored in a simulations/{event_name} subdirectory of the basemodel.

        Parameters
        ----------
        fiat_cfg : Path
            The file path to the FIAT configuration (toml) file.
        event_set_yaml : Path
            The path to the event description file.
        hazard_maps : Union[Path, List[Path]]
            The path to the hazard maps.
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
        self.input: Input = Input(
            fiat_cfg=fiat_cfg,
            event_set_yaml=event_set_yaml,
            hazard_maps=hazard_maps,
            _reduce_wildcards=["event"],
        )
        # NOTE: FIAT runs with full event sets with RPs. Name of event set is the stem of the event set file
        event_set_name = self.input.event_set_yaml.stem
        fiat_hazard = (
            self.input.fiat_cfg.parent / "simulations" / event_set_name / "hazard.nc"
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
        # TODO: hydromt_fiat does not automatically read the region, and region is needed!
        model.read()
        region_fn = Path(root / "exposure", "region.gpkg")
        region_gdf = gpd.read_file(region_fn).to_crs(4326)

        model.setup_region({"geom": region_gdf})

        # Make all paths relative in the config
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

        ## WARNING! code below is necessary for now, as hydromt_fiat cant deliver
        # READ the hazard catalog
        event_set: EventSet = EventSet.from_yaml(self.input.event_set_yaml)

        # extract all names
        hazard_names = [event["name"] for event in event_set.events]

        # filter out the right path names
        hazard_fns = []
        for name in hazard_names:
            for fn in self.input.hazard_maps:
                if name in fn.stem:
                    hazard_fns.append(fn)
                    break

        # get return periods
        rps = [1 / event_set.get_event(name).probability for name in hazard_names]

        # Setup the hazard map
        # TODO: for some reason hydromt_fiat removes any existing nodata values from flood maps and then later returns
        # a ValueError if the metadata of those same maps does not contain a nodata value. Here we impose a random -9999.
        model.setup_config(**config)
        model.setup_hazard(
            hazard_fns,
            map_type=self.params.map_type,
            rp=rps,
            risk_output=self.params.risk,
            var="flood_map",
            nodata=-9999.0,
        )
        # change root to simulation folder
        model.set_root(out_root, mode="w+")
        model.write_grid(fn=str(self.output.fiat_hazard))
        model.set_config("hazard.settings.var_as_band", True)
        model.set_config("hazard.file", self.output.fiat_hazard.name)

        # Write the config
        model.write_config()
