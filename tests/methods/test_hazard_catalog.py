from hydroflows.methods import HazardSet


def test_hazard_set(test_data_dir, tmp_path):
    event_set = test_data_dir / "events.yml"
    types = ["depth", "velocity"]
    depth_hazard_maps = ["depth_p_rp050.tif", "depth_p_rp010.tif"]
    velocity_hazard_map = ["velocity_p_rp050.tif", "velocity_p_rp010.tif"]
    event_set_out = tmp_path / "event_catalog_with_hazards.yml"
    input = {
        "event_set": event_set,
        "types": types,
        "depth_hazard_maps": depth_hazard_maps,
        "velocity_hazard_maps": velocity_hazard_map,
    }
    output = {"event_set": str(event_set_out)}

    # test running
    HazardSet(input=input, output=output).run()

    assert event_set_out.is_file()
