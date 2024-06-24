"""hydroflows: Automated and reproducible hydro model workflows."""

__version__ = "0.1.0.dev"

from pathlib import Path

from .method import Method
from .rule import Rule
from .workflow import Workflow

__all__ = [
    "__version__",
    "HYDROMT_CONFIG_DIR",
    "Method",
    "Rule",
    "Workflow",
]

# hydromt templates dir
PACKAGE_ROOT = Path(__file__).parent
HYDROMT_CONFIG_DIR = PACKAGE_ROOT / "templates" / "workflow" / "hydromt_config"
