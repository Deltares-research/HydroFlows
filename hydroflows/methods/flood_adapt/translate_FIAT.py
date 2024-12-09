# import required packages
from hydromt.log import setuplog
from hydromt_fiat.fiat import FiatModel


def translate_model(root, new_root):
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
