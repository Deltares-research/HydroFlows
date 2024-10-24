# import required packages
import os
from hydromt_fiat.fiat import FiatModel
from hydromt.log import setuplog
from pathlib import Path
import geopandas as gpd
from hydromt.config import configread


# Change the working directory to the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Build model von config file
root = Path(os.path.abspath("")) / "fiat_model_global"  
logger = setuplog("hydromt_fiat", log_level=10)
opt =  configread(Path(os.path.abspath("")) / "configuration_global.yml")

region = gpd.read_file(Path(os.path.abspath("")) / "data"/ "region.gpkg")

fm = FiatModel(
    root=root, mode="w+", logger=logger
)

# Build the new model
fm.build(region={"geom": region}, opt=opt,write=False)
fm.write()