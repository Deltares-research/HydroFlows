"""Data for examples and testing of HydroFlows."""
import json
import logging
from pathlib import Path

import pooch

__all__ = ["fetch_data"]

logger = logging.getLogger(__name__)

# update the base URL and registry with new versions of the data
# use create_artifact.py script in the p-drive hydroflows-test-data folder to update the registry
with open(Path(__file__).parent / "registry.json", "r") as f:
    DATABASE = json.load(f)
    BASE_URL: str = DATABASE["url"]
    REGISTRY: dict[str:str] = DATABASE["data"]
CACHE_DIR = Path("~", ".cache", "hydroflows").expanduser()
PROCESSORS = {
    "tar.gz": pooch.Untar,
    "zip": pooch.Unzip,
}


def unpack_processor(
    suffix: str,
    extract_dir: str = "./",
):
    """Select the right processor for unpacking."""
    if suffix not in PROCESSORS:
        return None
    processor = PROCESSORS[suffix](members=None, extract_dir=extract_dir)
    return processor


def fetch_data(
    data: str,
    output_dir: Path | str | None = None,
    sub_dir: bool = True,
) -> Path:
    """Fetch data by simply calling the function.

    Parameters
    ----------
    data : str
        The data to fetch.
    output_dir : Path | str | None
        The output directory to store the data.
        If None, the data will be stored in ~/.cache/hydroflows/<data>
    sub_dir : bool
        Whether to place the fetched data in a sub directory of the same name.
        I.e. if  the (tarred) dataset is named 'custom-data' a directory named
        'custom-data' is created in which the data are placed. By default True

    Returns
    -------
    Path
        The output directory where the data is stored
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if output_dir is None:
        output_dir = CACHE_DIR
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Quick check whether the data can be found
    choices_raw = list(REGISTRY.keys())
    choices = [item.split(".", 1)[0] for item in choices_raw]
    if data not in choices:
        raise ValueError(f"Choose one of the following: {choices}")
    idx = choices.index(data)

    # Setup Pooch
    retriever = pooch.create(
        path=CACHE_DIR,  # store archive to cache
        base_url=BASE_URL,
        registry=REGISTRY,
    )

    # Set the way of unpacking it
    suffix = choices_raw[idx].split(".", 1)[1]
    extract_dir = output_dir
    if sub_dir:
        extract_dir = Path(extract_dir, data)
    processor = unpack_processor(suffix, extract_dir=extract_dir)
    # Retrieve the data
    retriever.fetch(choices_raw[idx], processor=processor)

    return extract_dir


if __name__ == "__main__":
    for item in list(REGISTRY.keys()):
        fetch_data(item.split(".", 1)[0])
