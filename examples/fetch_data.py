"""Data for examples and testing of HydroFlows."""
from pathlib import Path

import pooch

PROCESSORS = {
    "tar.gz": pooch.Untar,
    "zip": pooch.Unzip,
}
REGISTRY = {
    "global-data.tar.gz": "dcd76132eda15ac45f77419c8c8c651b6fa1390b9b44a3c339df789bff6c8a07",
    "fiat-model.tar.gz": "42c8a1c7fe624f724e56b3c0604526fa79847de5c4f1b11da4133d470611aed1",
    "sfincs-model.tar.gz": "375d597969adb66ff62fb6511b40cddd560610074aacac9af71cab4d1d507631",
    "wflow-model.tar.gz": "0cdf0bdcd073285ac8e39643707eb3687d5d11b12e87697b999947e513b11023",
}


def unpack_processor(
    suffix: str,
):
    """Select the right processor for unpacking."""
    if suffix not in PROCESSORS:
        return None
    processor = PROCESSORS[suffix](members=None, extract_dir="./")
    return processor


def fetch(
    data: str,
    output_dir: Path | str,
):
    """Fetch data by simply calling the function."""
    # Quick check whether the data can be found
    choices_raw = list(REGISTRY.keys())
    choices = [item.split(".", 1)[0] for item in choices_raw]
    if data not in choices:
        raise ValueError(f"Choose one of the following: {choices}")
    idx = choices.index(data)

    # Path to current py-file
    pwd = Path(__file__).parent
    if not output_dir.is_absolute():
        output_dir = Path(pwd, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Setup Pooch
    retriever = pooch.create(
        path=output_dir,
        base_url="https://github.com/Deltares-research/hydroflows-data/releases/download/artifact-data",
        registry=REGISTRY,
    )

    # Set the way of unpacking it
    suffix = choices_raw[idx].split(".", 1)[1]
    processor = unpack_processor(suffix)
    # Retrieve the data
    retriever.fetch(choices_raw[idx], processor=processor)


if __name__ == "__main__":
    fetch()
    pass
