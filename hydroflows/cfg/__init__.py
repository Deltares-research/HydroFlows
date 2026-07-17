"""Python file solely for defining config related variables."""

from pathlib import Path

from .reader import read_recipe

__all__ = ["CFG_DIR", "read_recipe"]

CFG_DIR = Path(__file__).parent
