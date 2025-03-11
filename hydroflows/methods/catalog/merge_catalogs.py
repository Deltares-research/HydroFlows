"""Merge multiple data catalogs into one method."""

from pathlib import Path

from hydromt.data_catalog import DataCatalog
from pydantic import ConfigDict, model_validator

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["MergeCatalogs", "Input", "Output"]


class Input(Parameters):
    """Input parameters for the :py:class:`MergeCatalogs` method."""

    model_config = ConfigDict(extra="allow")

    catalog_path1: Path
    """The path to the first data catalog file to be merged."""

    catalog_path2: Path
    """The path to the second data catalog file to be merged."""

    @model_validator(mode="before")
    @classmethod
    def _set_abs_paths(cls, data: dict) -> dict:
        if isinstance(data, dict) and "catalog_paths" in data:
            data.update(**data["catalog_paths"])
            del data["catalog_paths"]
        return data


class Output(Parameters):
    """Output parameters for the :py:class:`MergeCatalogs` method."""

    merged_catalog_path: Path
    """The file path to the merged data catalog."""


class MergeCatalogs(Method):
    """Merge multiple data catalogs into one.

    Parameters
    ----------
    catalog_path1 : Path
        The path to the first data catalog file to be merged.
    catalog_path2: Path
        The path to the second data catalog file to be merged.
    merged_catalog_path: Path
        The path to the (output) merged data catalog file.
    catalog_paths: Path, Optional
        Additional catalog files to merge. For example
        `catalog_path3=Path("path/to/catalog3")`, `catalog_path4=Path("path/to/catalog4")`, etc.

    See Also
    --------
    :py:class:`MergeCatalogs Input <hydroflows.methods.catalog.merge_catalogs.Input>`
    :py:class:`MergeCatalogs Output <hydroflows.methods.catalog.merge_catalogs.Output>`
    """

    name: str = "merge_catalogs"

    _test_kwargs = dict(
        catalog_path1="catalog1.yml",
        catalog_path2="catalog2.yml",
        merged_catalog_path="catalog_merged.yml",
    )

    def __init__(
        self,
        catalog_path1: Path,
        catalog_path2: Path,
        merged_catalog_path: Path,
        **catalog_paths: dict[str, Path],
    ) -> None:
        self.input: Input = Input(
            catalog_path1=catalog_path1,
            catalog_path2=catalog_path2,
            catalog_paths=catalog_paths,
        )
        self.output: Output = Output(merged_catalog_path=merged_catalog_path)

    def _run(self):
        """Run the MergeCatalogs method."""
        data_libs = [self.input.catalog_path1, self.input.catalog_path2]
        for key in self.input.model_extra:
            data_libs.append(getattr(self.input, key))
        dc = DataCatalog(data_libs=data_libs)
        dc.to_yml(self.output.merged_catalog_path)
