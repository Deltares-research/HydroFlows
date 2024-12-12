"""Translate Delft_FIAT model to be compatible with FloodAdapt."""
from hydromt.log import setuplog
from hydromt_fiat.fiat import FiatModel


def translate_model(root, new_root):
    """
    Translate a FIAT model from the given root directory to a new root directory.

    Parameters
    ----------
    root : str or Path
        The path to the root directory of the existing FIAT model.
    new_root : str or Path
        The path to the new root directory where the translated FIAT model will be saved.

    Notes
    -----
    The translation involves renaming columns in both exposure databases and geometry
    objects to match the required format for the new model.
    """
    logger = setuplog("hydromt_fiat", log_level=10)
    fm = FiatModel(root=root, mode="w+", logger=logger)

    fm.read()

    exposure_db = fm.exposure.exposure_db
    exposure_geoms = fm.exposure.exposure_geoms
    trans_dict = {
        "object_id": "Object ID",
        "object_name": "Object Name",
        "primary_object_type": "Primary Object Type",
        "secondary_object_type": "Secondary Object Type",
        "max_damage_structure": "Max Potential Damage: Structure",
        "max_damage_content": "Max Potential Damage: Content",
        "max_damage_total": "Max Potential Damage: Total",
        "ground_flht": "Ground Floor Height",
        "extract_method": "Extraction Method",
        "ground_elevtn": "Ground Elevation",
        "fn_damage_structure": "Damage Function: Structure",
        "fn_damage_content": "Damage Function: Content",
    }
    exposure_db.rename(columns=trans_dict, inplace=True)
    for i in exposure_geoms:
        i.rename(columns=trans_dict, inplace=True)

    fm.exposure.exposure_db = exposure_db
    fm.exposure.exposure_geoms = exposure_geoms

    fm.set_root(new_root)
    fm.write()
