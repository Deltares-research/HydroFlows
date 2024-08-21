"""hydroflows: Automated and reproducible hydro model workflows."""

__version__ = "0.1.0.dev"


from .workflow import Method, Workflow

__all__ = [
    "__version__",
    "Workflow",
    "Method",
]
