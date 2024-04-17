from pathlib import Path

import pooch

if __name__ == "__main__":
    # Create the registry file from all files in data folder
    path = Path(__file__).parent
    pooch.make_registry(str(path / "data"), str(path / "registry.txt"), recursive=False)
