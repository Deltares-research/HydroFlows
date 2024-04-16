from pathlib import Path

import pooch

if __name__ == "__main__":
    path = Path(__file__).parent
    # get registry from remote to make sure it matches the data
    base_url = (
        "https://github.com/Deltares-research/HydroFlows/releases/download/test-data"
    )
    _ = pooch.retrieve(
        url=f"{base_url}/registry.txt",
        known_hash=None,
        path=path,
        fname="registry.txt",
    )
    # create registry
    test_data = pooch.create(
        # Use the default cache folder for the operating system
        path=path / "data",
        base_url=base_url,
        registry=None,
    )
    test_data.load_registry(path / "registry.txt")
    # fetch all the data
    for key in test_data.registry:
        test_data.fetch(key)
