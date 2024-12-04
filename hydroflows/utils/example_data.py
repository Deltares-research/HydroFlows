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
    DATABASE = json.load(f)["test_data"]
    BASE_URL = DATABASE["url"]
    REGISTRY = DATABASE["data"]
CACHE_DIR = Path("~", ".cache", "hydroflows").expanduser()
PROCESSORS = {
    "tar.gz": pooch.Untar,
    "zip": pooch.Unzip,
}


def unpack_processor(
    suffix: str,
):
    """Select the right processor for unpacking."""
    if suffix not in PROCESSORS:
        return None
    processor = PROCESSORS[suffix](members=None, extract_dir="./")
    return processor


def fetch_data(
    data: str,
    output_dir: Path | str | None = None,
) -> Path:
    """Fetch data by simply calling the function.

    Parameters
    ----------
    data : str
        The data to fetch.
    output_dir : Path | str | None
        The output directory to store the data.
        If None, the data will be stored in ~/.cache/hydroflows/<data>

    Returns
    -------
    Path
        The output directory where the data is stored
    """
    if output_dir is None:
        output_dir = CACHE_DIR / data

    # Quick check whether the data can be found
    choices_raw = list(REGISTRY.keys())
    choices = [item.split(".", 1)[0] for item in choices_raw]
    if data not in choices:
        raise ValueError(f"Choose one of the following: {choices}")
    idx = choices.index(data)

    # Setup Pooch
    retriever = pooch.create(
        path=output_dir,
        base_url=BASE_URL,
        registry=REGISTRY,
    )

    # create the output directory
    logger.info(f"Fetching data: {data} to {output_dir.as_posix()}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set the way of unpacking it
    suffix = choices_raw[idx].split(".", 1)[1]
    processor = unpack_processor(suffix)
    # Retrieve the data
    retriever.fetch(choices_raw[idx], processor=processor)

    return output_dir
