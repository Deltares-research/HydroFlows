from pathlib import Path

from hydromt.data_catalog import DataCatalog

from hydroflows.methods.catalog.merge_catalogs import MergeCatalogs


def test_merge_catalogs(global_catalog: Path, tmp_path: Path):
    dc = DataCatalog(global_catalog)
    sources_keys = list(dc.sources.keys())
    sources_items = list(dc.sources.values())

    dc._sources = {sources_keys[0]: sources_items[0]}
    catalog1 = Path(tmp_path, "catalog1.yml")
    dc.to_yml(catalog1)

    catalog2 = Path(tmp_path, "catalog2.yml")
    dc._sources = {sources_keys[1]: sources_items[1]}
    dc.to_yml(catalog2)

    catalog3 = Path(tmp_path, "catalog3.yml")
    dc._sources = {sources_keys[-1]: sources_items[-1]}
    dc.to_yml(catalog3)

    merged_catalog = Path(tmp_path, "catalog_merged.yml")

    # test with three catalogs (one extra)
    m = MergeCatalogs(
        catalog_path1=catalog1,
        catalog_path2=catalog2,
        catalog_path3=catalog3,
        merged_catalog_path=merged_catalog,
    )
    assert "catalog_path3" in m.input.model_extra
    assert isinstance(m.input.catalog_path3, Path)

    m.run_with_checks()

    dc_out = DataCatalog(merged_catalog)
    assert sources_keys[0] in dc_out.sources
    assert sources_keys[-1] in dc_out.sources
