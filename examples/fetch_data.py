"""Data for examples and testing of HydroFlows."""
import json
import sys
from pathlib import Path

import pooch

# update the base URL and registry with new versions of the data
BASE_URL = "doi:10.5281/zenodo.14164946"
REGISTRY = {
    "global-data.tar.gz": "dcd76132eda15ac45f77419c8c8c651b6fa1390b9b44a3c339df789bff6c8a07",
    "fiat-model.tar.gz": "42c8a1c7fe624f724e56b3c0604526fa79847de5c4f1b11da4133d470611aed1",
    "sfincs-model.tar.gz": "0ed6910fe4e52f23210e7607c70c163b1ad0ad5f5d2ea8a68497b84c705e4d18",
    "wflow-model.tar.gz": "0cdf0bdcd073285ac8e39643707eb3687d5d11b12e87697b999947e513b11023",
}

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


def fetch(
    data: str,
    output_dir: Path | str,
):
    """Fetch data by simply calling the function."""
    print(f"Fetching data: {data} to {output_dir}")

    # Quick check whether the data can be found
    choices_raw = list(REGISTRY.keys())
    choices = [item.split(".", 1)[0] for item in choices_raw]
    if data not in choices:
        raise ValueError(f"Choose one of the following: {choices}")
    idx = choices.index(data)

    # create the output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    # Setup Pooch
    retriever = pooch.create(
        path=output_dir,
        base_url=BASE_URL,
        registry=REGISTRY,
    )

    # Set the way of unpacking it
    suffix = choices_raw[idx].split(".", 1)[1]
    processor = unpack_processor(suffix)
    # Retrieve the data
    retriever.fetch(choices_raw[idx], processor=processor)


if __name__ == "__main__":
    if len(sys.argv) == 1 and "snakemake" not in globals():
        pwd = Path(__file__).parent
        cache_dir = Path(pwd, "data")
        for item in REGISTRY:
            name = item.split(".", 1)[0]
            fetch(data=name, output_dir=cache_dir / name)
    else:
        if len(sys.argv) == 2:  # hydroflows run
            args = json.loads(sys.argv[1])
            output_file = Path(args.get("output", {}).get("output_file"))
        elif "snakemake" in globals():
            snakemake = globals()["snakemake"]
            output_file = Path(snakemake.output.output_file)
        data = output_file.stem.split(".", 2)[0]
        output_dir = output_file.parent
        fetch(data=data, output_dir=output_dir)
