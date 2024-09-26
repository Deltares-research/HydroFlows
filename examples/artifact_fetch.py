"""Data for examples and testing of HydroFlows."""
from pathlib import Path

import pooch


def fetch():
    """Fetch data by simply calling the function."""
    # Path to current py-file
    path = Path(__file__).parent
    # Setup Pooch
    retriever = pooch.create(
        path=Path(path, "data/global-data"),
        base_url="https://github.com/Deltares-research/hydroflows-data/releases/download/artifact-data",
        registry={
            "artifact-data.tar.gz": "c614cbc78b08a3ca873d982cb573535b04a9d1d3012c4452c0074cbd795eeab8",
        },
    )
    # Set the way of unpacking it
    tar = pooch.Untar(members=None, extract_dir="./")
    # Retrieve the data
    retriever.fetch("artifact-data.tar.gz", processor=tar)
    pass


if __name__ == "__main__":
    fetch()
    pass
