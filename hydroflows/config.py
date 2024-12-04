"""Hydroflow global config settings."""

# hydromt templates dir
from pathlib import Path

__all__ = ["HYDROMT_CONFIG_DIR"]

PACKAGE_ROOT = Path(__file__).parent
HYDROMT_CONFIG_DIR = PACKAGE_ROOT / "cfg"
