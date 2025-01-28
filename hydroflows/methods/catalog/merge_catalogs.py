""""""

from pathlib import Path

from hydromt.data_catalog import DataCatalog
from pydantic import ConfigDict, model_validator

from hydroflows.workflow.method import Method
from hydroflows.workflow.method_parameters import Parameters

__all__ = ["MergeCatalogs"]


class Input(Parameters):
    """"""

    model_config = ConfigDict(extra="allow")

    catalog_path1: Path

    catalog_path2: Path

    @model_validator(mode="before")
    @classmethod
    def _set_abs_paths(cls, data: dict) -> dict:
        if isinstance(data, dict) and "catalog_paths" in data:
            for i, path in enumerate(data["catalog_paths"]):
                data[f"catalog_path{i+3}"] = Path(path)
            del data["catalog_paths"]
        return data


class Output(Parameters):
    """"""

    merged_catalog_path: Path


class MergeCatalogs(Method):
    """"""

    name = "merge_catalogs"

    _test_kwargs = dict(
        catalog_path1="catalog1.yml",
        catalog_path2="catalog2.yml",
        merged_catalog_path="catalog_merged.yml",
    )

    def __init__(
        self,
        catalog_path1: Path,
        catalog_path2: Path,
        *catalog_paths: Path,
        merged_catalog_path: Path,
    ) -> None:
        self.input: Input = Input(
            catalog_path1=catalog_path1,
            catalog_path2=catalog_path2,
            catalog_paths=catalog_paths,
        )
        self.output: Output = Output(merged_catalog_path=merged_catalog_path)

    def run(self):
        """"""
        data_libs = [self.input.catalog_path1, self.input.catalog_path2]
        for key in self.input.model_extra:
            data_libs.append(getattr(self.input, key))
        dc = DataCatalog(data_libs=data_libs)
        dc.to_yml(self.output.merged_catalog_path)
