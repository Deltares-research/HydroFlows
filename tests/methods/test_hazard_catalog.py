from hydroflows.methods import HazardCatalog


def test_hazard_catalog(test_data_dir, tmp_path):
    event_catalog = test_data_dir / "events.yml"
    types = ["depth", "velocity"]
    hazards = [
        ["depth_p_rp050.tif", "depth_p_rp010.tif"],
        ["velocity_p_rp050.tif", "velocity_p_rp010.tif"]
    ]
    event_catalog_out = tmp_path / "event_catalog_with_hazards.yml"
    input = {
        "event_catalog": event_catalog,
        "types": types,
        "hazards": hazards
    }
    output = {
        "event_catalog": str(event_catalog_out)
    }

    # test running
    HazardCatalog(input=input, output=output).run()

    assert event_catalog_out.is_file()
