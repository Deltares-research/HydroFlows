"""Small temporary file for checking hydromt-wflow availability."""

import importlib

HAS_HYDROMT_WFLOW = importlib.util.find_spec("hydromt_wflow") is not None
